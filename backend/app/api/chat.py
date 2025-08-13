from fastapi import APIRouter, Body
from app.rag.chroma_setup import collection
from app.rag.embeddings import get_embedding
from app.tools.moderation import is_prompt_flagged
from app.tools.distance import normalize_distances

# ⬇️ NEW: cache helpers
from app.db.db import (
    normalize_prompt,
    cache_lookup_exact,
    cache_lookup_fuzzy,
    cache_upsert,
)

import os
import openai
from dotenv import load_dotenv

MAX_ACCEPTABLE_RAW_DISTANCE = 1.19  
FUZZY_THRESHOLD = 0.70              # trigram similarity threshold

router = APIRouter()
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Pricing via env (USD per 1K tokens) to avoid stale hardcodes
IN_PRICE = float(os.getenv("OPENAI_INPUT_PRICE_PER_1K", "0.0005"))
OUT_PRICE = float(os.getenv("OPENAI_OUTPUT_PRICE_PER_1K", "0.0015"))

def log_valid_results(results):
    print("\n📊 Top Matches:")
    for i, (doc, meta, raw_dist, norm_dist) in enumerate(results):
        print(f"📚 #{i+1}: {meta.get('title', 'N/A')}")
        print(f"📏 Raw distance: {raw_dist:.4f} | Normalized: {norm_dist:.4f}")
        print(f"📝 Summary (trimmed): {doc[:100]}...\n")


@router.post("/")
async def get_book_recommendation(query: str = Body(..., embed=True)):
    # Basic validation + moderation
    if not query or len(query.strip()) < 3:
        return {"error": "Interogare prea scurtă. Te rog reformulează."}

    if is_prompt_flagged(query):
        return {
            "recommended_title": None,
            "explanation": "Te rog formulează întrebarea într-un mod respectuos. Îți stau la dispoziție cu recomandări literare.",
            "source_summary": None
        }

    # ---------- CACHE: exact then fuzzy ----------
    prompt_norm = normalize_prompt(query)

    # 1) exact cache
    hit = await cache_lookup_exact(prompt_norm)
    if hit:
        return {
            "recommended_title": None,                # you can fill from metadata if you later store it
            "explanation": hit["output_data"],        # cached final text
            "source_summary": None,                   # optional to store later
            "from_cache": True,
            "model_name": hit["model_name"],
            "generation_cost_usd": float(hit["generation_cost_usd"]),
            "generated_at": hit["generated_at"]
        }

    # 2) fuzzy fallback (pg_trgm)
    near = await cache_lookup_fuzzy(prompt_norm, threshold=FUZZY_THRESHOLD)
    if near:
        near["generation_cost_usd"] = float(near["generation_cost_usd"])
        return {
            "recommended_title": None,
            "explanation": near["output_data"],
            "source_summary": None,
            "from_cache": True,
            "model_name": near["model_name"],
            "generation_cost_usd": near["generation_cost_usd"],
            "generated_at": near["generated_at"]
        }

    # ---------- RAG: find top doc ----------
    print(f"🔍 Query: {query}")
    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    normalized_distances = normalize_distances(distances)

    valid_results = []
    for i, (doc, meta, raw_dist, norm_dist) in enumerate(zip(documents, metadatas, distances, normalized_distances)):
        if doc and meta:
            valid_results.append((doc, meta, raw_dist, norm_dist))

    if not valid_results:
        # Miss in RAG too
        return {
            "recommended_title": None,
            "explanation": "Îmi pare rău, dar nu am găsit nicio carte potrivită în baza de date curentă.",
            "source_summary": None,
            "from_cache": False,
            "model_name": None,
            "generation_cost_usd": 0.0
        }

    log_valid_results(valid_results)

    # Use only the top result for the GPT explanation
    top_doc, top_meta, raw_dist, norm_dist = valid_results[0]

    if raw_dist > MAX_ACCEPTABLE_RAW_DISTANCE:
        print(f"⚠️ Top result too far (raw distance: {raw_dist:.4f}) — skipping GPT.")
        return {
            "recommended_title": None,
            "explanation": "Îmi pare rău, dar nu am găsit nicio carte relevantă pentru întrebarea ta.",
            "source_summary": None,
            "normalized_distance": norm_dist,
            "from_cache": False,
            "model_name": None,
            "generation_cost_usd": 0.0
        }

    # ---------- LLM generation ----------
    model_name = "gpt-3.5-turbo"  # keep aligned with your account
    prompt = f"""
Ținând cont de interogarea: "{query}", oferă o recomandare pe baza următoarei cărți, care este cea mai apropiată semantic dintre toate cele din baza de date (scor: {norm_dist:.4f}).

Titlu: {top_meta.get("title", "N/A")}
Rezumat: {top_doc.strip()}

Scrie o recomandare prietenoasă, clară și scurtă. Explică de ce această carte răspunde cerinței utilizatorului, fără a inventa alte opțiuni.
Raspunsul trebuie sa fie de maxim 50 de cuvinte.
""".strip()

    # Synchronous OpenAI call is fine here; if needed, offload to threadpool later.
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )

    gpt_reply = response["choices"][0]["message"]["content"].strip()

    # Cost calculation from usage (avoid hardcoding prices here; use env)
    usage = response.get("usage", {}) or {}
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    generation_cost_usd = (prompt_tokens / 1000.0) * IN_PRICE + (completion_tokens / 1000.0) * OUT_PRICE

    print("🧠 GPT Explanation:\n", gpt_reply)
    print(f"💰 Tokens in/out: {prompt_tokens}/{completion_tokens} -> cost ${generation_cost_usd:.6f}")

    # ---------- Persist to cache ----------
    await cache_upsert(
        prompt_norm,
        output_format="text",
        output_data=gpt_reply,
        model_name=model_name,
        generation_cost_usd=generation_cost_usd,
    )

    # ---------- Response ----------
    return {
        "recommended_title": top_meta.get("title"),
        "explanation": gpt_reply,
        "source_summary": top_doc,
        "normalized_distance": norm_dist,
        "from_cache": False,
        "model_name": model_name,
        "generation_cost_usd": generation_cost_usd
    }

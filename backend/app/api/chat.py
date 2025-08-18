from fastapi import APIRouter, Body
from app.rag.chroma_setup import collection
from app.rag.embeddings import get_embedding
from app.tools.moderation import is_prompt_flagged
from app.tools.distance import normalize_distances

from app.db.db import (
    normalize_prompt,
    cache_lookup_exact,
    cache_lookup_fuzzy,
    cache_upsert,
)

import os
import re
import openai
from dotenv import load_dotenv

# --- NEW: optional diacritics-insensitive matching
try:
    from unidecode import unidecode  # pip install unidecode
except Exception:
    unidecode = lambda s: s

MAX_ACCEPTABLE_RAW_DISTANCE = 1.19
FUZZY_THRESHOLD = 0.70

router = APIRouter()
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

IN_PRICE = float(os.getenv("OPENAI_INPUT_PRICE_PER_1K", "0.0005"))
OUT_PRICE = float(os.getenv("OPENAI_OUTPUT_PRICE_PER_1K", "0.0015"))

def log_valid_results(results):
    print("\n📊 Top Matches:")
    for i, (doc, meta, raw_dist, norm_dist) in enumerate(results):
        print(f"📚 #{i+1}: {meta.get('title', 'N/A')}")
        print(f"   👤 Author: {meta.get('author', 'N/A')}")
        print(f"📏 Raw distance: {raw_dist:.4f} | Normalized: {norm_dist:.4f}")
        print(f"📝 Summary (trimmed): {doc[:100]}...\n")

# --- NEW: parse explicit author intent e.g., "de Liviu Rebreanu"
AUTHOR_PAT = re.compile(r"\b(?:de|by)\s+([A-Za-zÀ-ž\-\.\s']{2,})", re.IGNORECASE)

IMAGE_KEYWORDS = [
    # English
    "generate me an image",
    "show me an image",
    "imagine an image",
    "draw me",
    "picture of",

    # Romanian
    "generează o imagine",
    "arată-mi o imagine",
    "imaginează-ți o imagine",
    "desenează",
    "o poză cu"
]


def wants_image(query: str) -> bool:
    q_lower = query.lower()
    return any(kw in q_lower for kw in IMAGE_KEYWORDS)

def _extract_image_link(img_result: dict) -> str:
    """
    Return a browser-renderable link for the first image:
    - Prefer hosted URL if present
    - Else fall back to data URL from b64_json
    """
    if not img_result or "data" not in img_result or not img_result["data"]:
        raise ValueError("Image API returned empty payload")

    first = img_result["data"][0]
    if "url" in first and first["url"]:
        return first["url"]

    b64 = first.get("b64_json")
    if b64:
        return f"data:image/png;base64,{b64}"

    raise ValueError("No image URL or b64_json found in image response")


def extract_author(q: str) -> str | None:
    m = AUTHOR_PAT.search(q)
    if not m:
        return None
    return unidecode(m.group(1)).strip().lower()


def norm(s: str) -> str:
    return unidecode((s or "").strip().lower())


@router.post("/")
async def get_book_recommendation(query: str = Body(..., embed=True)):
    if not query or len(query.strip()) < 3:
        return {"error": "Interogare prea scurtă. Te rog reformulează."}

    if is_prompt_flagged(query):
        return {
            "recommended_title": None,
            "explanation": "Te rog formulează întrebarea într-un mod respectuos. Îți stau la dispoziție cu recomandări literare.",
            "source_summary": None,
            "prompt_norm": normalize_prompt(query),     # <-- include for frontend
        }

    prompt_norm = normalize_prompt(query)
    
    # ---------- IMAGE GENERATION BRANCH ----------
    if wants_image(query):
        img_prompt_norm = "[img] " + prompt_norm

        # Check cache for image first
        hit = await cache_lookup_exact(img_prompt_norm)
        if hit:
            return {
                "image_url": hit["output_data"],
                "prompt_norm": img_prompt_norm,
                "from_cache": True,
                "model_name": hit["model_name"],
                "generation_cost_usd": float(hit["generation_cost_usd"]),
                "generated_at": hit["generated_at"]
            }

        print("🖼 Image generation requested")
        try:
            img_result = openai.Image.create(
                model="gpt-image-1",  # use "gpt-image-1" if your org is verified
                prompt=query,
                size="1024x1024"
            )

            # Safely extract image link or b64
            first = img_result.get("data", [{}])[0]
            if "url" in first and first["url"]:
                image_url = first["url"]
            elif "b64_json" in first and first["b64_json"]:
                image_url = f"data:image/png;base64,{first['b64_json']}"
            else:
                raise ValueError("No image URL or b64_json in API response")

        except Exception as e:
            print(f"⚠️ Image generation failed: {e}")
            return {
                "image_url": None,
                "prompt_norm": img_prompt_norm,
                "from_cache": False,
                "model_name": "dall-e-3",
                "generation_cost_usd": 0.0,
                "error": "Image generation is temporarily unavailable."
            }

        generation_cost_usd = 0.02  # adjust if you have exact pricing

        # Save image to cache
        await cache_upsert(
            img_prompt_norm,
            output_format="image",
            output_data=image_url,
            model_name="gpt-image-1",
            generation_cost_usd=generation_cost_usd,
        )

        return {
            "image_url": image_url,
            "prompt_norm": img_prompt_norm,
            "from_cache": False,
            "model_name": "gpt-image-1",
            "generation_cost_usd": generation_cost_usd
        }


    # ---------- CACHE: exact then fuzzy ----------
    hit = await cache_lookup_exact(prompt_norm)
    if hit:
        return {
            "recommended_title": None,
            "explanation": hit["output_data"],
            "source_summary": None,
            "from_cache": True,
            "model_name": hit["model_name"],
            "generation_cost_usd": float(hit["generation_cost_usd"]),
            "generated_at": hit["generated_at"],
            "prompt_norm": prompt_norm,               # <-- include
        }

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
            "generated_at": near["generated_at"],
            "prompt_norm": prompt_norm,              
        }

    # ---------- RAG: retrieve ----------
    print(f"🔍 Query: {query}")
    query_embedding = get_embedding(query)
    # widen a bit to improve author hit probability
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,  # was 3
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    normalized_distances = normalize_distances(distances)

    valid_results = []
    for doc, meta, raw_dist, norm_dist in zip(documents, metadatas, distances, normalized_distances):
        if doc and meta:
            valid_results.append((doc, meta, raw_dist, norm_dist))

    if not valid_results:
        return {
            "recommended_title": None,
            "explanation": "Îmi pare rău, dar nu am găsit nicio carte potrivită în baza de date curentă.",
            "source_summary": None,
            "from_cache": False,
            "model_name": None,
            "generation_cost_usd": 0.0,
            "prompt_norm": prompt_norm,               # <-- include
        }

    # --- NEW: author-aware re-rank
    requested_author = extract_author(query)
    if requested_author:
        author_hits = [
            (doc, meta, raw_dist, norm_dist)
            for (doc, meta, raw_dist, norm_dist) in valid_results
            if norm(meta.get("author")) == requested_author
        ]
        if author_hits:
            valid_results = author_hits  # narrow to matching author

    # safety: always pick the closest by raw distance
    valid_results.sort(key=lambda x: x[2])  # ascending raw_dist
    log_valid_results(valid_results)

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
            "generation_cost_usd": 0.0,
            "prompt_norm": prompt_norm,               # <-- include
        }

    # ---------- LLM generation ----------
    model_name = "gpt-3.5-turbo"
    # Optional: nudge the LLM to honor author if present
    author_clause = f"\nAutor cerut: {requested_author}" if requested_author else ""
    prompt = f"""
Ținând cont de interogarea: "{query}", oferă o recomandare pe baza următoarei cărți, care este cea mai apropiată semantic dintre toate cele din baza de date (scor: {norm_dist:.4f}).{author_clause}

Titlu: {top_meta.get("title", "N/A")}
Autor: {top_meta.get("author", "N/A")}
Rezumat: {top_doc.strip()}

Scrie o recomandare prietenoasă, clară și scurtă. Explică de ce această carte răspunde cerinței utilizatorului, fără a inventa alte opțiuni.
Răspunsul trebuie să fie de maxim 50 de cuvinte.
""".strip()

    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )

    gpt_reply = response["choices"][0]["message"]["content"].strip()

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
        "generation_cost_usd": generation_cost_usd,
        "prompt_norm": prompt_norm,                   # <-- include for frontend thumbs
    }

from fastapi import APIRouter, Body
from app.rag.chroma_setup import collection
from app.rag.embeddings import get_embedding
from app.tools.moderation import is_prompt_flagged
from app.tools.distance import normalize_distances
import openai
import os
from dotenv import load_dotenv

MAX_ACCEPTABLE_RAW_DISTANCE = 1.19  # or adjust as needed

router = APIRouter()
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def log_valid_results(results):
    print("\n📊 Top Matches:")
    for i, (doc, meta, raw_dist, norm_dist) in enumerate(results):
        print(f"📚 #{i+1}: {meta.get('title', 'N/A')}")
        print(f"📏 Raw distance: {raw_dist:.4f} | Normalized: {norm_dist:.4f}")
        print(f"📝 Summary (trimmed): {doc[:100]}...\n")


@router.post("/")
def get_book_recommendation(query: str = Body(..., embed=True)):
    if not query or len(query.strip()) < 3:
        return {"error": "Interogare prea scurtă. Te rog reformulează."}

    if is_prompt_flagged(query):
        return {
            "recommended_title": None,
            "explanation": "Te rog formulează întrebarea într-un mod respectuos. Îți stau la dispoziție cu recomandări literare.",
            "source_summary": None
        }

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
        return {
            "recommended_title": None,
            "explanation": "Îmi pare rău, dar nu am găsit nicio carte potrivită în baza de date curentă.",
            "source_summary": None
        }

    # 🧾 Log top 3 results in console (for developer visibility)
    log_valid_results(valid_results)

    # ✅ Use only the top result for the GPT explanation
    top_doc, top_meta, raw_dist, norm_dist = valid_results[0]
    
    
    if raw_dist > MAX_ACCEPTABLE_RAW_DISTANCE:
        print(f"⚠️ Top result too far (raw distance: {raw_dist:.4f}) — skipping GPT.")
        return {
            "recommended_title": None,
            "explanation": "Îmi pare rău, dar nu am găsit nicio carte relevantă pentru întrebarea ta.",
            "source_summary": None,
            "normalized_distance": norm_dist
    }

    prompt = f"""
Ținând cont de interogarea: "{query}", oferă o recomandare pe baza următoarei cărți, care este cea mai apropiată semantic dintre toate cele din baza de date (scor: {norm_dist:.4f}).

Titlu: {top_meta.get("title", "N/A")}
Rezumat: {top_doc.strip()}

Scrie o recomandare prietenoasă, clară și scurtă. Explică de ce această carte răspunde cerinței utilizatorului, fără a inventa alte opțiuni.
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    gpt_reply = response['choices'][0]['message']['content'].strip()

    print("🧠 GPT Explanation:\n", gpt_reply)

    return {
        "recommended_title": top_meta.get("title"),
        "explanation": gpt_reply,
        "source_summary": top_doc,
        "normalized_distance": norm_dist
    }
   
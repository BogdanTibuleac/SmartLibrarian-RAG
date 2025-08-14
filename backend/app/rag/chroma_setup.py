# app/rag/chroma_setup.py
import os
import json
import re
import chromadb
from chromadb.config import Settings
from app.rag.embeddings import get_embedding

# -----------------------------------------------------------------------------
# Chroma client & collection
# -----------------------------------------------------------------------------
client = chromadb.Client(
    Settings(
        persist_directory="app/rag/.chroma",  # persisted vector store
        anonymized_telemetry=False,           # avoid noisy telemetry in logs
    )
)
collection = client.get_or_create_collection(name="book_summaries")

# -----------------------------------------------------------------------------
# Helpers: parse "Title – Author" and normalize metadata
# -----------------------------------------------------------------------------
_DASH_SPLIT = re.compile(r"\s*[–—-]\s*")  # en dash, em dash, hyphen

def _parse_title_author(raw: str) -> tuple[str, str | None]:
    """
    Split strings like 'Ion – Liviu Rebreanu' into ('Ion', 'Liviu Rebreanu').
    Falls back to (raw, None) if no dash-based author is present.
    """
    raw = (raw or "").strip()
    parts = _DASH_SPLIT.split(raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw, None

# -----------------------------------------------------------------------------
# Load / rebuild
# -----------------------------------------------------------------------------
def load_books_to_chroma(data_path: str) -> None:
    """
    Loads book summaries into Chroma. If the collection already has data,
    this will NO-OP unless CHROMA_FORCE_RELOAD=1 is set (then it rebuilds).
    """
    global collection  # must be at top before any usage

    force_reload = os.getenv("CHROMA_FORCE_RELOAD", "0") == "1"

    if collection.count() > 0 and not force_reload:
        print("⚠️  Chroma already initialized. Skipping load. (Set CHROMA_FORCE_RELOAD=1 to rebuild.)")
        print_chroma_contents()
        return

    if force_reload and collection.count() > 0:
        print("♻️  Force reload requested. Dropping and recreating collection...")
        client.delete_collection("book_summaries")
        collection = client.get_or_create_collection(name="book_summaries")

    with open(data_path, encoding="utf-8") as f:
        books = json.load(f)

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []
    embs: list[list[float]] = []

    for book in books:
        raw_title: str = book.get("title", "")
        summary: str = book.get("summary", "")

        clean_title, author = _parse_title_author(raw_title)

        # Chroma metadata must be primitives; stringify themes lists
        themes_val = book.get("themes", [])
        if isinstance(themes_val, list):
            themes_val = ", ".join(themes_val)
        elif themes_val is None:
            themes_val = ""

        ids.append(raw_title)  # keep raw string (unique enough here)
        docs.append(summary)
        metas.append(
            {
                "title": clean_title,    # clean title only
                "author": author or "",  # critical for author-aware ranking
                "themes": themes_val,    # always a string
            }
        )
        embs.append(get_embedding(summary))

    # Bulk add for performance + ensure aligned lengths
    collection.add(documents=docs, ids=ids, metadatas=metas, embeddings=embs)

    print(f"✅ Indexed {collection.count()} book summaries.")
    print_chroma_contents()

# -----------------------------------------------------------------------------
# Diagnostics
# -----------------------------------------------------------------------------
def print_chroma_contents() -> None:
    all_docs = collection.get(include=["documents", "metadatas"])
    print("\n📚 ChromaDB Contents:")
    for i in range(len(all_docs["ids"])):
        meta = all_docs["metadatas"][i] or {}
        print(f"- Title : {meta.get('title', all_docs['ids'][i])}")
        print(f"  Author: {meta.get('author', '')}")
        print(f"  Meta  : {meta}")
        print("  ---")

# -----------------------------------------------------------------------------
# Hard reset utility (use manually when you intentionally change schema)
# -----------------------------------------------------------------------------
def reset_and_reload(data_path: str) -> None:
    global collection  # must be at top
    print("🧹 Dropping collection 'book_summaries' and reloading...")
    client.delete_collection("book_summaries")
    collection = client.get_or_create_collection(name="book_summaries")
    load_books_to_chroma(data_path)

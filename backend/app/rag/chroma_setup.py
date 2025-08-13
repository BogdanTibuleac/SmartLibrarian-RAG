import os
import json
import chromadb
from chromadb.config import Settings
from app.rag.embeddings import get_embedding

# Initialize Chroma client
client = chromadb.Client(Settings(
    persist_directory="app/rag/.chroma",  # persisted vector store
    anonymized_telemetry=False
))

collection = client.get_or_create_collection(name="book_summaries")


def load_books_to_chroma(data_path: str):
    if collection.count() > 0:
        print("⚠️  Chroma already initialized. Skipping load.")
        print_chroma_contents()
        return

    with open(data_path, encoding="utf-8") as f:
        books = json.load(f)

    for book in books:
        title = book["title"]
        summary = book["summary"]

        embedding = get_embedding(summary)

        collection.add(
            documents=[summary],
            ids=[title],
            embeddings=[embedding],
            metadatas=[{"title": title}]
        )

    print(f"✅ Indexed {collection.count()} book summaries.")
    print_chroma_contents()


def print_chroma_contents():
    all_docs = collection.get(include=["documents", "metadatas"])
    print("\n📚 ChromaDB Contents:")
    for i in range(len(all_docs["ids"])):
        print(f"- Title: {all_docs['ids'][i]}")
        print(f"  Summary: {all_docs['documents'][i]}")
        print(f"  Metadata: {all_docs['metadatas'][i]}")
        print("  ---")

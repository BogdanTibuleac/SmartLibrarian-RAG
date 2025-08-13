from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.rag.chroma_setup import load_books_to_chroma

app = FastAPI(title="Smart Librarian RAG")

# ✅ Allow frontend requests from Vite (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or use ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load embeddings on startup
@app.on_event("startup")
def init_rag_store():
    load_books_to_chroma("app/data/book_summaries.json")

# ✅ Mount the chat router at /chat/
app.include_router(chat_router, prefix="/chat")  # Note: /chat/ in frontend

@app.get("/")
def root():
    return {"status": "Smart Librarian backend is running."}

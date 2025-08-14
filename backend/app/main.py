# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.chat import router as chat_router
from app.rag.chroma_setup import load_books_to_chroma
from app.db.db import get_pool, close_pool 
from app.api import feedback

app = FastAPI(title="Smart Librarian RAG")
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])

# CORS for Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: warm the DB pool and load your RAG store
@app.on_event("startup")
async def startup():
    # 1) Initialize DB pool early (fail fast if DATABASE_URL is wrong)
    await get_pool()

    # 2) Load embeddings / collection (runs sync; push to thread to avoid blocking loop)
    await run_in_threadpool(load_books_to_chroma, "app/data/book_summaries.json")

# Shutdown: close DB pool
@app.on_event("shutdown")
async def shutdown():
    await close_pool()

# Routes
app.include_router(chat_router, prefix="/chat")

@app.get("/")
def root():
    return {"status": "Smart Librarian backend is running."}

# Optional: quick DB health probe
@app.get("/health/db")
async def health_db():
    pool = await get_pool()
    async with pool.acquire() as con:
        await con.execute("SELECT 1;")
    return {"db": "ok"}

# app/api/feedback.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Literal
from app.db.db import get_pool

router = APIRouter()

class FeedbackPayload(BaseModel):
    prompt_norm: str
    thumb: Literal["up", "down"]

@router.post("/")
async def submit_feedback(payload: FeedbackPayload):
    pool = await get_pool()
    async with pool.acquire() as con:
        if payload.thumb == "up":
            updated = await con.execute(
                """
                UPDATE qa_cache
                   SET liked = TRUE
                 WHERE input_prompt_normalized = $1
                """,
                payload.prompt_norm.lower().strip()
            )
            return {"status": "ok", "action": "liked", "rows": updated}
        else:
            # Strategy A: TTL from generation time (preferred, keeps semantics clean)
            updated = await con.execute(
                """
                UPDATE qa_cache
                   SET liked = FALSE
                 WHERE input_prompt_normalized = $1
                """,
                payload.prompt_norm.lower().strip()
            )
            return {"status": "ok", "action": "disliked", "rows": updated}

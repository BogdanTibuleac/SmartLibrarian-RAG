from fastapi import APIRouter, Body, HTTPException
from app.db import cache_upsert, normalize_prompt

router = APIRouter()

class LikePayload(BaseModel):
    input_prompt: str
    output_format: str        # 'text' | 'image' | 'audio'
    output_data: str          # text or /media/... url
    model_name: str
    generation_cost_usd: float

@router.post("/like")
async def like_answer(payload: LikePayload):
    prompt_norm = normalize_prompt(payload.input_prompt)

    # Upsert into qa_cache only now (on Like)
    await cache_upsert(
        prompt_norm,
        output_format=payload.output_format,
        output_data=payload.output_data,
        model_name=payload.model_name,
        generation_cost_usd=payload.generation_cost_usd,
    )
    return {"ok": True}

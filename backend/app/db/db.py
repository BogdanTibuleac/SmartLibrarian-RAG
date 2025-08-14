import os, asyncio, re
from typing import Optional, Tuple, Dict, Any
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# -------- Normalization (exact/fuzzy use the same canonical prompt) ----------
_ws_re = re.compile(r"\s+")
def normalize_prompt(s: str) -> str:
    return _ws_re.sub(" ", s.strip().lower())

# -------- Pool management -----------------------------------------------------
_pool: Optional[asyncpg.pool.Pool] = None

async def get_pool() -> asyncpg.pool.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

# -------- Cache ops -----------------------------------------------------------
async def cache_lookup_exact(prompt_norm: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """
            SELECT output_format, output_data, model_name, generation_cost_usd, generated_at
            FROM qa_cache
            WHERE input_prompt_normalized = $1
              AND liked IS TRUE
            """,
            prompt_norm,
        )
        if row:
            await con.execute(
                """
                UPDATE qa_cache
                SET retrieval_count = retrieval_count + 1,
                    last_accessed_at = now()
                WHERE input_prompt_normalized = $1
                  AND liked IS TRUE
                """,
                prompt_norm,
            )
            return dict(row)
        return None

async def cache_lookup_fuzzy(prompt_norm: str, threshold: float = 0.50) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as con:
        row = await con.fetchrow(
            """
            SELECT input_prompt_normalized, output_format, output_data, model_name,
                   generation_cost_usd, generated_at,
                   similarity(input_prompt_normalized, $1) AS sim
            FROM qa_cache
            WHERE liked IS TRUE
              AND input_prompt_normalized % $1
            ORDER BY sim DESC
            LIMIT 1
            """,
            prompt_norm,
        )
        if row and float(row["sim"]) >= threshold:
            await con.execute(
                """
                UPDATE qa_cache
                SET retrieval_count = retrieval_count + 1,
                    last_accessed_at = now()
                WHERE input_prompt_normalized = $1
                  AND liked IS TRUE
                """,
                row["input_prompt_normalized"],
            )
            return {
                "output_format": row["output_format"],
                "output_data": row["output_data"],
                "model_name": row["model_name"],
                "generation_cost_usd": row["generation_cost_usd"],
                "generated_at": row["generated_at"],
            }
        return None

async def cache_upsert(prompt_norm: str, *, output_format: str, output_data: str,
                       model_name: str, generation_cost_usd: float):
    pool = await get_pool()
    async with pool.acquire() as con:
        await con.execute(
            """
            INSERT INTO qa_cache (
              input_prompt_normalized, output_format, output_data,
              model_name, generation_cost_usd, generated_at, liked
            )
            VALUES ($1, $2, $3, $4, $5, now(), NULL)
            ON CONFLICT (input_prompt_normalized) DO UPDATE
            SET output_format = EXCLUDED.output_format,
                output_data   = EXCLUDED.output_data,
                model_name    = EXCLUDED.model_name,
                generation_cost_usd = EXCLUDED.generation_cost_usd,
                generated_at  = EXCLUDED.generated_at,
                liked         = NULL,                 -- reset on regeneration
                last_accessed_at = now()
            """,
            prompt_norm, output_format, output_data, model_name, generation_cost_usd
        )

# backend/scripts/ttl_cleanup.py
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

TTL_DAYS = int(os.getenv("QA_CACHE_TTL_DAYS", "3"))
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in environment.")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        deleted = await conn.execute(
            """
            DELETE FROM qa_cache
             WHERE liked = FALSE
               AND now() - generated_at > ($1::text || ' days')::interval
            """,
            str(TTL_DAYS),
        )
        print(f"[TTL CLEANUP] {deleted}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())

"""Backfill: link existing ingredients to USDA foods via full-text search.

Usage (from repo root):
    cd apps/backend-api && uv run python ../../scripts/match_ingredient_foods.py

Reads DATABASE_URL from the environment, falling back to the local dev default.
Idempotent and safe to re-run: only touches rows that are unmatched or were
auto-matched before ('confirmed'/'rejected' rows set by a human are left alone).
"""

import asyncio
import os

import asyncpg

# Keep in sync with FOOD_MATCH_THRESHOLD in app/api/v1/recipes.py
FOOD_MATCH_THRESHOLD = 0.05

# For each candidate ingredient, pick the single best-ranked food above threshold.
MATCH_SQL = """
UPDATE ingredients i
SET food_id = m.food_id,
    food_match = 'auto'
FROM (
    SELECT DISTINCT ON (i2.id) i2.id AS ingredient_id, f.id AS food_id
    FROM ingredients i2
    JOIN foods f ON f.search_vec @@ plainto_tsquery('english', i2.name)
    WHERE (i2.food_id IS NULL OR i2.food_match = 'auto')
      AND ts_rank(f.search_vec, plainto_tsquery('english', i2.name)) > $1
    ORDER BY i2.id, ts_rank(f.search_vec, plainto_tsquery('english', i2.name)) DESC
) m
WHERE i.id = m.ingredient_id
"""


async def main() -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://recipie:recipie@localhost:5432/recipie",
    ).replace("postgresql+asyncpg://", "postgresql://")

    print("Connecting to database ...")
    conn = await asyncpg.connect(dsn)
    try:
        before = await conn.fetchval(
            "SELECT count(*) FROM ingredients WHERE food_id IS NULL OR food_match = 'auto'"
        )
        status = await conn.execute(MATCH_SQL, FOOD_MATCH_THRESHOLD)
        matched = await conn.fetchval(
            "SELECT count(*) FROM ingredients WHERE food_id IS NOT NULL"
        )
        total = await conn.fetchval("SELECT count(*) FROM ingredients")
        print(f"  Candidates examined: {before}")
        print(f"  {status}")
        print(f"Done. {matched}/{total} ingredients now linked to a USDA food.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

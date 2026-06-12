from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food import Food


async def search_foods(db: AsyncSession, query: str, limit: int = 20) -> list[Food]:
    """Full-text search foods by keyword, ranked by relevance.

    Mirrors the query in scripts/match_ingredient_foods.py: matches against the
    GIN-indexed `search_vec` and orders by ts_rank. No threshold is applied so a
    human picker always sees candidates. `plainto_tsquery` matches whole words,
    not prefixes.
    """
    q = (query or "").strip()
    if not q:
        return []
    tsquery = func.plainto_tsquery("english", q)
    rank = func.ts_rank(Food.search_vec, tsquery)
    stmt = (
        select(Food)
        .where(Food.search_vec.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())

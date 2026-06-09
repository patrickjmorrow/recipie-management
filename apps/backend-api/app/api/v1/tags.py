import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse

router = APIRouter(prefix="/tags", tags=["tags"])

_DEPRECATION_WINDOW = timedelta(days=7)


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    include_deprecated: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tag).order_by(Tag.name)
    if not include_deprecated:
        stmt = stmt.where(Tag.deprecated_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tag = Tag(name=payload.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: uuid.UUID,
    payload: TagCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.name = payload.name
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id).options(selectinload(Tag.recipes))
    )
    tag = result.scalar_one()

    if not tag.recipes:
        await db.delete(tag)
        await db.commit()
        return None

    tag.deprecated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "deprecated", "message": "Tag deprecated; will be purged in 7 days"}


@router.post("/purge", status_code=status.HTTP_200_OK)
async def purge_deprecated_tags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - _DEPRECATION_WINDOW
    result = await db.execute(
        select(Tag).where(Tag.deprecated_at.is_not(None), Tag.deprecated_at <= cutoff)
    )
    tags = result.scalars().all()
    for tag in tags:
        await db.delete(tag)
    await db.commit()
    return {"purged": len(tags)}

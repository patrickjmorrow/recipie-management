import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    body: str | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    recipe_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewer_display_name: str | None = None
    rating: int
    body: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

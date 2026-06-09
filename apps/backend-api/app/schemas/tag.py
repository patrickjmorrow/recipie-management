import uuid
from datetime import datetime

from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str
    deprecated_at: datetime | None = None

    model_config = {"from_attributes": True}

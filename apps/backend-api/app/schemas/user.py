import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserUpdate(BaseModel):
    display_name: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    # See Recipe: load server_default/onupdate columns via RETURNING so they're
    # never left expired after a write (avoids MissingGreenlet on serialization).
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="author")  # noqa: F821
    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user")  # noqa: F821
    reviews: Mapped[list["RecipeReview"]] = relationship(back_populates="reviewer")  # noqa: F821

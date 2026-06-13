import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RecipeReview(Base):
    __tablename__ = "recipe_reviews"
    __table_args__ = (UniqueConstraint("recipe_id", "reviewer_id", name="uq_recipe_review_user"),)
    # See Recipe: load server_default/onupdate columns via RETURNING so they're
    # never left expired after a write (avoids MissingGreenlet on serialization).
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recipe: Mapped["Recipe"] = relationship(back_populates="reviews")  # noqa: F821
    reviewer: Mapped["User"] = relationship(back_populates="reviews")  # noqa: F821

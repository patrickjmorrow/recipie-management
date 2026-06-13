import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.tag import recipe_tags


class Recipe(Base):
    __tablename__ = "recipes"
    # Fetch server_default / onupdate columns (created_at, updated_at) inline via
    # RETURNING on INSERT/UPDATE. Without this they're left expired after a write,
    # and serializing them triggers a lazy load — which fails under async with
    # MissingGreenlet during response validation.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    image_key: Mapped[str | None] = mapped_column(String(512))
    recipie_metadata: Mapped[dict | None] = mapped_column(JSONB)
    avg_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    # Per-serving macros cached from the linked USDA foods (see services/nutrition.recipe_macros).
    # NULL means "never computed" — the detail GET lazily backfills; writes recompute.
    energy_kcal_per_serving: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    protein_g_per_serving: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    carbs_g_per_serving: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    author: Mapped["User"] = relationship(back_populates="recipes")  # noqa: F821
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(  # noqa: F821
        back_populates="recipe",
        order_by="RecipeIngredient.sort_order",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary=recipe_tags, back_populates="recipes", lazy="selectin"
    )
    reviews: Mapped[list["RecipeReview"]] = relationship(  # noqa: F821
        back_populates="recipe", cascade="all, delete-orphan"
    )

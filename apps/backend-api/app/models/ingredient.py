import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Link to the canonical USDA food for nutrition. Stored once per ingredient
    # name and inherited by every recipe that uses it.
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id", ondelete="SET NULL"))
    # Provenance of the link: 'auto' (full-text guess), 'confirmed' (human),
    # 'rejected' (human said no match). Lets re-matching skip human decisions.
    food_match: Mapped[str | None] = mapped_column(String(20))

    food: Mapped["Food | None"] = relationship(lazy="joined")  # noqa: F821
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    recipe: Mapped["Recipe"] = relationship(back_populates="recipe_ingredients")  # noqa: F821
    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_ingredients")

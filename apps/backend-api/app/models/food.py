from sqlalchemy import Computed, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fdc_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    energy_kcal: Mapped[float | None] = mapped_column(Numeric)
    protein_g: Mapped[float | None] = mapped_column(Numeric)
    fat_g: Mapped[float | None] = mapped_column(Numeric)
    sat_fat_g: Mapped[float | None] = mapped_column(Numeric)
    carbs_g: Mapped[float | None] = mapped_column(Numeric)
    fiber_g: Mapped[float | None] = mapped_column(Numeric)
    sugar_g: Mapped[float | None] = mapped_column(Numeric)
    sodium_mg: Mapped[float | None] = mapped_column(Numeric)
    search_vec: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', name)", persisted=True),
    )

    # food_portions is keyed by the fdc_id business key, not foods.id, so the
    # importer can populate it independently. viewonly: never written via ORM.
    portions: Mapped[list["FoodPortion"]] = relationship(  # noqa: F821
        primaryjoin="foreign(FoodPortion.fdc_id) == Food.fdc_id",
        viewonly=True,
    )

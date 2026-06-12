from sqlalchemy import Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FoodPortion(Base):
    """USDA household measures (e.g. "1 cup", "1 large") -> gram weight, per food.

    Density varies per food, so volume/count units can only be converted to grams
    with these per-fdc_id portions. Keyed by fdc_id (not foods.id) so the importer
    can populate it independently of the foods upsert.
    """

    __tablename__ = "food_portions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fdc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    modifier: Mapped[str | None] = mapped_column(Text)
    # gram_weight is the weight of `amount` units, so grams-per-unit = gram_weight / amount.
    amount: Mapped[float | None] = mapped_column(Numeric)
    gram_weight: Mapped[float | None] = mapped_column(Numeric)

"""search upgrade: pantry staples flag + macro/fridge indexes

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-12

"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


# Ingredients safe to assume the cook already has, so "what's in my fridge"
# ignores them when counting what a recipe is still missing. Deliberately
# excludes butter/tortillas etc. — only genuinely-assumed pantry items.
STAPLE_NAMES = [
    "salt", "kosher salt", "sea salt", "table salt",
    "pepper", "black pepper", "white pepper",
    "water",
    "olive oil", "vegetable oil", "canola oil", "cooking oil",
    "sugar", "granulated sugar",
    "flour", "all-purpose flour",
    "baking soda", "baking powder",
    "garlic powder", "onion powder", "paprika", "cumin",
    "oregano", "basil", "thyme", "cinnamon",
    "vanilla extract",
    "soy sauce", "vinegar", "white vinegar",
]


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ingredients ADD COLUMN is_staple BOOLEAN NOT NULL DEFAULT false"
    )
    # Seed existing rows; new rows default to false and can be promoted later.
    names = ", ".join(f"'{n}'" for n in STAPLE_NAMES)
    op.execute(
        f"UPDATE ingredients SET is_staple = true WHERE lower(name) IN ({names})"
    )

    # Macro range filters need an energy index (0007 only added protein/carbs).
    op.execute(
        "CREATE INDEX ix_recipes_energy ON recipes (energy_kcal_per_serving) "
        "WHERE energy_kcal_per_serving IS NOT NULL"
    )
    # Speeds the fridge group-by + ingredient_id IN (...) conditional count.
    op.execute(
        "CREATE INDEX ix_recipe_ingredients_recipe_ingredient "
        "ON recipe_ingredients (recipe_id, ingredient_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recipe_ingredients_recipe_ingredient")
    op.execute("DROP INDEX IF EXISTS ix_recipes_energy")
    op.execute("ALTER TABLE ingredients DROP COLUMN IF EXISTS is_staple")

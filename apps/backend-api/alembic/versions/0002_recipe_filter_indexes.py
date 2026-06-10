"""recipe filter indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-09

"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_recipes_title_pattern",
        "recipes",
        ["title"],
        postgresql_ops={"title": "text_pattern_ops"},
    )
    op.execute(
        "CREATE INDEX ix_recipes_metadata_gin ON recipes "
        "USING gin (recipie_metadata jsonb_path_ops)"
    )
    op.create_index(
        "ix_recipe_ingredients_ingredient_id",
        "recipe_ingredients",
        ["ingredient_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recipe_ingredients_ingredient_id", table_name="recipe_ingredients")
    op.execute("DROP INDEX IF EXISTS ix_recipes_metadata_gin")
    op.drop_index("ix_recipes_title_pattern", table_name="recipes")

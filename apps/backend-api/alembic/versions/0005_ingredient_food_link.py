"""link ingredients to USDA foods

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-11

"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE ingredients
            ADD COLUMN food_id    INTEGER REFERENCES foods(id) ON DELETE SET NULL,
            ADD COLUMN food_match VARCHAR(20)
    """)
    op.execute("CREATE INDEX ingredients_food_id_idx ON ingredients (food_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ingredients_food_id_idx")
    op.execute("ALTER TABLE ingredients DROP COLUMN IF EXISTS food_match")
    op.execute("ALTER TABLE ingredients DROP COLUMN IF EXISTS food_id")

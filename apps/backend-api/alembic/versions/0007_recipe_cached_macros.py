"""cache per-serving macros on recipes (for nutrition browse sections)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-12

"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE recipes
            ADD COLUMN energy_kcal_per_serving NUMERIC(8, 2),
            ADD COLUMN protein_g_per_serving   NUMERIC(8, 2),
            ADD COLUMN carbs_g_per_serving     NUMERIC(8, 2)
    """)
    # Partial indexes: nutrition sections only ever scan rows with cached macros.
    op.execute(
        "CREATE INDEX ix_recipes_protein ON recipes (protein_g_per_serving DESC) "
        "WHERE protein_g_per_serving IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_recipes_carbs ON recipes (carbs_g_per_serving ASC) "
        "WHERE carbs_g_per_serving IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recipes_carbs")
    op.execute("DROP INDEX IF EXISTS ix_recipes_protein")
    op.execute("ALTER TABLE recipes DROP COLUMN IF EXISTS carbs_g_per_serving")
    op.execute("ALTER TABLE recipes DROP COLUMN IF EXISTS protein_g_per_serving")
    op.execute("ALTER TABLE recipes DROP COLUMN IF EXISTS energy_kcal_per_serving")

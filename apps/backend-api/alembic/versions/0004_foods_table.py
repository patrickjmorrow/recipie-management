"""foods table with USDA nutrient data

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-11

"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE foods (
            id          SERIAL PRIMARY KEY,
            fdc_id      INTEGER UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            category    TEXT,
            energy_kcal NUMERIC,
            protein_g   NUMERIC,
            fat_g       NUMERIC,
            sat_fat_g   NUMERIC,
            carbs_g     NUMERIC,
            fiber_g     NUMERIC,
            sugar_g     NUMERIC,
            sodium_mg   NUMERIC,
            search_vec  TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', name)) STORED
        )
    """)
    op.execute("CREATE INDEX foods_search_idx ON foods USING GIN (search_vec)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS foods")

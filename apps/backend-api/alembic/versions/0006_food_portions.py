"""food_portions table (USDA household measures -> gram weight)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-11

"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE food_portions (
            id          SERIAL PRIMARY KEY,
            fdc_id      INTEGER NOT NULL,
            description TEXT,
            modifier    TEXT,
            amount      NUMERIC,
            gram_weight NUMERIC
        )
    """)
    op.execute("CREATE INDEX food_portions_fdc_id_idx ON food_portions (fdc_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS food_portions")

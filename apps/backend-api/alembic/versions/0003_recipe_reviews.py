"""recipe reviews and ratings

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-11

"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("avg_rating", sa.Numeric(3, 2), nullable=True))
    op.add_column(
        "recipes",
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "recipe_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipe_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column(
            "rating",
            sa.Integer(),
            sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_recipe_reviews_rating"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "reviewer_id", name="uq_recipe_review_user"),
    )
    op.create_index("ix_recipe_reviews_recipe_id", "recipe_reviews", ["recipe_id"])
    op.create_index("ix_recipe_reviews_reviewer_id", "recipe_reviews", ["reviewer_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_reviews_reviewer_id", table_name="recipe_reviews")
    op.drop_index("ix_recipe_reviews_recipe_id", table_name="recipe_reviews")
    op.drop_table("recipe_reviews")
    op.drop_column("recipes", "review_count")
    op.drop_column("recipes", "avg_rating")

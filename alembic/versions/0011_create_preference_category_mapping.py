"""create preference_category_mapping table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preference_category_mapping",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("preference_tag", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("preference_tag", "category", name="uq_preference_category_mapping"),
    )


def downgrade() -> None:
    op.drop_table("preference_category_mapping")

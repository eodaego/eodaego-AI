"""create recommendation_history table

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-18

"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("is_success", sa.Boolean(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("failure_status_code", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("prompt_template_id", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_history")

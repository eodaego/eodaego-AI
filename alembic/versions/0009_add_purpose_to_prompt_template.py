"""add purpose column to prompt_template

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-14

"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prompt_template",
        sa.Column("purpose", sa.String(length=20), nullable=False, server_default="chat"),
    )
    op.alter_column("prompt_template", "purpose", server_default=None)


def downgrade() -> None:
    op.drop_column("prompt_template", "purpose")

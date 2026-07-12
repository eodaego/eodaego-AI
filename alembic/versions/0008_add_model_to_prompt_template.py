"""add model column to prompt_template

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-12

"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prompt_template", sa.Column("model", sa.String(length=100), nullable=False))


def downgrade() -> None:
    op.drop_column("prompt_template", "model")

"""create catalog tables (animal, plant)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10

"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "animal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("msg_seq", sa.Integer(), nullable=False, unique=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("scientific_name", sa.String(length=200), nullable=True),
        sa.Column("english_name", sa.String(length=200), nullable=True),
        sa.Column("classification", sa.String(length=200), nullable=True),
        sa.Column("distribution", sa.String(length=500), nullable=True),
        sa.Column("diet", sa.String(length=500), nullable=True),
        sa.Column("registered_date", sa.String(length=20), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("location_name", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "plant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("msg_seq", sa.Integer(), nullable=False, unique=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("registered_date", sa.String(length=20), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("plant")
    op.drop_table("animal")

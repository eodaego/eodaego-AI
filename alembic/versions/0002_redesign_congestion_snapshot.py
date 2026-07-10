"""redesign congestion snapshot, drop operating hours snapshot stub

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-10

"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("operating_hours_snapshot")
    op.drop_table("congestion_snapshot")
    op.create_table(
        "congestion_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_ref_key", sa.String(length=100), nullable=False),
        sa.Column("congestion_level", sa.String(length=20), nullable=False),
        sa.Column("congestion_message", sa.String(length=200), nullable=False),
        sa.Column("population_min", sa.Integer(), nullable=False),
        sa.Column("population_max", sa.Integer(), nullable=False),
        sa.Column("forecast", sa.JSON(), nullable=False),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("congestion_snapshot")
    op.create_table(
        "congestion_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_ref_key", sa.String(length=100), nullable=False),
        sa.Column("congestion_level", sa.Float(), nullable=False),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "operating_hours_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_ref_key", sa.String(length=100), nullable=False),
        sa.Column("raw_hours_text", sa.String(length=500), nullable=False),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

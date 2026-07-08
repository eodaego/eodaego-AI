"""create initial tables

Revision ID: 0001
Revises:
Create Date: 2026-07-09

"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "schedule_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("trigger_config", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
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


def downgrade() -> None:
    op.drop_table("operating_hours_snapshot")
    op.drop_table("congestion_snapshot")
    op.drop_table("schedule_config")
    op.drop_table("prompt_template")

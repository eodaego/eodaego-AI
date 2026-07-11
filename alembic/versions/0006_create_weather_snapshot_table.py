"""create weather_snapshot table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-11

"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weather_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_ref_key", sa.String(length=100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("humidity", sa.Integer(), nullable=False),
        sa.Column("precipitation_type", sa.String(length=20), nullable=False),
        sa.Column("wind_speed", sa.Float(), nullable=False),
        sa.Column("sky_condition", sa.String(length=20), nullable=True),
        sa.Column("hourly_forecast", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("weather_snapshot")

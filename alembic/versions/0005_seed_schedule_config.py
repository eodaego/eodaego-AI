"""seed schedule_config rows for congestion/catalog/operating_hours jobs

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-10

"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

schedule_config = sa.table(
    "schedule_config",
    sa.column("job_id", sa.String),
    sa.column("trigger_type", sa.String),
    sa.column("trigger_config", sa.String),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.bulk_insert(
        schedule_config,
        [
            {
                "job_id": "crawl_congestion",
                "trigger_type": "interval",
                "trigger_config": "minutes=15",
                "is_active": True,
            },
            {
                "job_id": "crawl_catalog",
                "trigger_type": "cron",
                "trigger_config": "0 3 1 */3 *",
                "is_active": True,
            },
            {
                "job_id": "crawl_operating_hours",
                "trigger_type": "cron",
                "trigger_config": "0 3 1 */3 *",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM schedule_config WHERE job_id IN "
            "('crawl_congestion', 'crawl_catalog', 'crawl_operating_hours')"
        )
    )

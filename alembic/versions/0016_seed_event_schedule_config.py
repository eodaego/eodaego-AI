"""seed schedule_config row for crawl_event job

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
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
                "job_id": "crawl_event",
                "trigger_type": "cron",
                "trigger_config": "30 3 * * *",
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM schedule_config WHERE job_id = 'crawl_event'"))

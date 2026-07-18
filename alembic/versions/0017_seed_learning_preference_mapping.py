"""seed learning preference category mapping

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-18

"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

preference_category_mapping = sa.table(
    "preference_category_mapping",
    sa.column("preference_tag", sa.String),
    sa.column("category", sa.String),
)

_SEED_ROWS = [
    ("LEARNING", "동물나라"),
    ("LEARNING", "자연나라"),
]


def upgrade() -> None:
    op.bulk_insert(
        preference_category_mapping,
        [{"preference_tag": tag, "category": category} for tag, category in _SEED_ROWS],
    )


def downgrade() -> None:
    # 0012와 동일한 이유로 TRUNCATE 대신 targeted delete: 관리자가 이후 추가한 매핑까지
    # 지우지 않기 위함.
    conn = op.get_bind()
    for tag, category in _SEED_ROWS:
        conn.execute(
            sa.text(
                "DELETE FROM preference_category_mapping "
                "WHERE preference_tag = :tag AND category = :category"
            ),
            {"tag": tag, "category": category},
        )

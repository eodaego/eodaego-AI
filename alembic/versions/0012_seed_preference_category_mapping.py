"""seed preference_category_mapping with existing hardcoded mapping

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

preference_category_mapping = sa.table(
    "preference_category_mapping",
    sa.column("preference_tag", sa.String),
    sa.column("category", sa.String),
)


_SEED_ROWS = [
    ("ANIMAL", "동물나라"),
    ("NATURE", "자연나라"),
    ("NATURE", "조경시설"),
    ("ACTIVITY", "재미나라"),
    ("ACTIVITY", "체험시설"),
    ("ACTIVITY", "운동 및 대관시설"),
    ("RELAXATION", "조경시설"),
]


def upgrade() -> None:
    op.bulk_insert(
        preference_category_mapping,
        [{"preference_tag": tag, "category": category} for tag, category in _SEED_ROWS],
    )


def downgrade() -> None:
    # 관리자가 이 마이그레이션 이후 추가한 매핑까지 지우지 않도록, 이 마이그레이션이
    # 삽입한 7개 (preference_tag, category) 쌍만 targeted delete한다(전체 TRUNCATE 금지).
    conn = op.get_bind()
    for tag, category in _SEED_ROWS:
        conn.execute(
            sa.text(
                "DELETE FROM preference_category_mapping "
                "WHERE preference_tag = :tag AND category = :category"
            ),
            {"tag": tag, "category": category},
        )

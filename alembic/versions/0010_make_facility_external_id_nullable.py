"""make facility external_id nullable

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-15

"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("facility", "external_id", nullable=True)


def downgrade() -> None:
    # 관리자가 생성한 시설(예: 출입문)의 external_id가 NULL로 남아있으면 이 다운그레이드가
    # NOT NULL 제약 위반으로 실패한다 — 롤백 전 해당 행을 먼저 정리해야 한다.
    op.alter_column("facility", "external_id", nullable=False)

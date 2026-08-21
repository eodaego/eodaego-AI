"""create prompt_template_provider table and migrate model column

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-21

"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_template_provider",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prompt_template_id",
            sa.Integer(),
            sa.ForeignKey("prompt_template.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(
        """
        INSERT INTO prompt_template_provider
            (prompt_template_id, provider, model, priority, is_enabled)
        SELECT id, 'SUH_AIDER', model, 1, true
        FROM prompt_template
        """
    )
    op.drop_column("prompt_template", "model")


def downgrade() -> None:
    op.add_column("prompt_template", sa.Column("model", sa.String(length=100), nullable=True))
    op.execute(
        """
        UPDATE prompt_template
        SET model = subquery.model
        FROM (
            SELECT DISTINCT ON (prompt_template_id) prompt_template_id, model
            FROM prompt_template_provider
            ORDER BY prompt_template_id, priority ASC, id ASC
        ) AS subquery
        WHERE prompt_template.id = subquery.prompt_template_id
        """
    )
    # upgrade 이후 새로 만들어진 템플릿에 provider가 하나도 없으면 위 UPDATE로도 채워지지
    # 않아 model이 NULL로 남는다 — 다음 alter_column(nullable=False)이 실패하지 않도록
    # 빈 문자열로 채운다.
    op.execute("UPDATE prompt_template SET model = '' WHERE model IS NULL")
    op.alter_column("prompt_template", "model", nullable=False)
    op.drop_table("prompt_template_provider")

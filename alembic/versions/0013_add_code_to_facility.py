"""add code column to facility

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("facility", sa.Column("code", sa.String(length=50), nullable=True))
    op.create_unique_constraint("uq_facility_code", "facility", ["code"])


def downgrade() -> None:
    op.drop_constraint("uq_facility_code", "facility", type_="unique")
    op.drop_column("facility", "code")

"""seed facility with 11 real park entrance gates

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

facility = sa.table(
    "facility",
    sa.column("category", sa.String),
    sa.column("name", sa.String),
    sa.column("code", sa.String),
    sa.column("latitude", sa.Float),
    sa.column("longitude", sa.Float),
)

_SEED_ROWS = [
    ("정문", "MAIN_GATE", 37.548042, 127.074766),
    ("회관문", "HOEGWAN_GATE", 37.545787, 127.075568),
    ("남문", "SOUTH_GATE", 37.544401, 127.080086),
    ("구의문", "GUI_GATE", 37.545950, 127.087362),
    ("동문1", "EAST_GATE_1", 37.547227, 127.089257),
    ("동문2", "EAST_GATE_2", 37.548708, 127.089555),
    ("후문", "REAR_GATE", 37.551206, 127.088769),
    ("북문1", "NORTH_GATE_1", 37.552337, 127.083347),
    ("북문2", "NORTH_GATE_2", 37.552617, 127.080908),
    ("서문", "WEST_GATE", 37.551120, 127.076510),
    ("능동문", "NEUNGDONG_GATE", 37.546895, 127.074286),
]


def upgrade() -> None:
    op.bulk_insert(
        facility,
        [
            {"category": "출입문", "name": name, "code": code, "latitude": lat, "longitude": lng}
            for name, code, lat, lng in _SEED_ROWS
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    for _, code, _, _ in _SEED_ROWS:
        conn.execute(sa.text("DELETE FROM facility WHERE code = :code"), {"code": code})

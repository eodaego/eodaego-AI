from sqlalchemy import inspect


def test_alembic_upgrade_head_creates_all_tables(db_engine):
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())

    assert {
        "prompt_template",
        "schedule_config",
        "congestion_snapshot",
        "operating_hours_snapshot",
    }.issubset(table_names)

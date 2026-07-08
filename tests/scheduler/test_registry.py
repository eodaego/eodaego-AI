from apscheduler.schedulers.background import BackgroundScheduler

from app.domains.crawling.model import ScheduleConfig
from app.scheduler.registry import bootstrap_scheduler


def _noop() -> None:
    pass


def test_bootstrap_scheduler_registers_only_active_jobs(db_session):
    db_session.add(
        ScheduleConfig(
            job_id="dummy_job",
            trigger_type="interval",
            trigger_config="hours=2",
            is_active=True,
        )
    )
    db_session.add(
        ScheduleConfig(
            job_id="inactive_job",
            trigger_type="interval",
            trigger_config="hours=6",
            is_active=False,
        )
    )
    db_session.commit()

    scheduler = BackgroundScheduler()
    bootstrap_scheduler(
        scheduler, db_session, job_registry={"dummy_job": _noop, "inactive_job": _noop}
    )

    job_ids = {job.id for job in scheduler.get_jobs()}
    assert job_ids == {"dummy_job"}


def test_bootstrap_scheduler_skips_jobs_without_registry_entry(db_session):
    db_session.add(
        ScheduleConfig(
            job_id="unregistered_job",
            trigger_type="cron",
            trigger_config="0 * * * *",
            is_active=True,
        )
    )
    db_session.commit()

    scheduler = BackgroundScheduler()
    bootstrap_scheduler(scheduler, db_session, job_registry={})

    assert scheduler.get_jobs() == []


def test_bootstrap_scheduler_isolates_malformed_trigger_config(db_session):
    db_session.add(
        ScheduleConfig(
            job_id="valid_job",
            trigger_type="interval",
            trigger_config="hours=2",
            is_active=True,
        )
    )
    db_session.add(
        ScheduleConfig(
            job_id="malformed_job",
            trigger_type="interval",
            trigger_config="hours=not-a-number",
            is_active=True,
        )
    )
    db_session.commit()

    scheduler = BackgroundScheduler()
    bootstrap_scheduler(
        scheduler, db_session, job_registry={"valid_job": _noop, "malformed_job": _noop}
    )

    job_ids = {job.id for job in scheduler.get_jobs()}
    assert job_ids == {"valid_job"}

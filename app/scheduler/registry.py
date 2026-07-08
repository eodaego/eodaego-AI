from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.crawling.model import ScheduleConfig

JobRegistry = dict[str, Callable[[], None]]

# 실제 크롤링 job(congestion_job, catalog_job)은 후속 계획에서 등록한다.
JOB_REGISTRY: JobRegistry = {}


def build_trigger(trigger_type: str, trigger_config: str) -> IntervalTrigger | CronTrigger:
    if trigger_type == "interval":
        hours = int(trigger_config.removeprefix("hours="))
        return IntervalTrigger(hours=hours)
    if trigger_type == "cron":
        return CronTrigger.from_crontab(trigger_config)
    raise ValueError(f"unsupported trigger_type: {trigger_type}")


def bootstrap_scheduler(
    scheduler: BackgroundScheduler, db: Session, job_registry: JobRegistry
) -> None:
    active_configs = db.scalars(
        select(ScheduleConfig).where(ScheduleConfig.is_active.is_(True))
    ).all()
    for schedule_config in active_configs:
        job_fn = job_registry.get(schedule_config.job_id)
        if job_fn is None:
            continue
        trigger = build_trigger(schedule_config.trigger_type, schedule_config.trigger_config)
        scheduler.add_job(job_fn, trigger=trigger, id=schedule_config.job_id, replace_existing=True)

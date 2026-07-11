import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.catalog.service import crawl_catalog_job
from app.domains.crawling.model import ScheduleConfig
from app.domains.crawling.service import crawl_congestion_job
from app.domains.facility.service import crawl_operating_hours_job
from app.domains.weather.service import crawl_weather_job

logger = logging.getLogger(__name__)

JobRegistry = dict[str, Callable[[], None]]

JOB_REGISTRY: JobRegistry = {
    "crawl_congestion": crawl_congestion_job,
    "crawl_catalog": crawl_catalog_job,
    "crawl_operating_hours": crawl_operating_hours_job,
    "crawl_weather": crawl_weather_job,
}


def build_trigger(trigger_type: str, trigger_config: str) -> IntervalTrigger | CronTrigger:
    if trigger_type == "interval":
        unit, _, value = trigger_config.partition("=")
        if unit not in ("minutes", "hours"):
            raise ValueError(f"unsupported interval unit: {unit}")
        return IntervalTrigger(**{unit: int(value)})
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
        try:
            trigger = build_trigger(schedule_config.trigger_type, schedule_config.trigger_config)
            scheduler.add_job(
                job_fn, trigger=trigger, id=schedule_config.job_id, replace_existing=True
            )
        except Exception:
            # 잘못된 trigger_config로 앱 기동 전체가 실패하지 않도록 개별 job 실패를 격리한다.
            logger.warning(
                "스케줄 등록 실패, 건너뜀: job_id=%s trigger_type=%s trigger_config=%s",
                schedule_config.job_id,
                schedule_config.trigger_type,
                schedule_config.trigger_config,
                exc_info=True,
            )

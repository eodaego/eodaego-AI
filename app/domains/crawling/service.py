from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.crawling.model import ScheduleConfig
from app.domains.crawling.schema import ScheduleConfigCreate, ScheduleConfigUpdate


def create_schedule_config(db: Session, data: ScheduleConfigCreate) -> ScheduleConfig:
    schedule = ScheduleConfig(**data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedule_configs(db: Session) -> list[ScheduleConfig]:
    return list(db.scalars(select(ScheduleConfig)).all())


def get_schedule_config(db: Session, schedule_id: int) -> ScheduleConfig | None:
    return db.get(ScheduleConfig, schedule_id)


def update_schedule_config(
    db: Session, schedule: ScheduleConfig, data: ScheduleConfigUpdate
) -> ScheduleConfig:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule_config(db: Session, schedule: ScheduleConfig) -> None:
    db.delete(schedule)
    db.commit()

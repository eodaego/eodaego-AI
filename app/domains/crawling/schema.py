from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScheduleConfigCreate(BaseModel):
    job_id: str
    trigger_type: Literal["interval", "cron"]
    trigger_config: str
    is_active: bool = True


class ScheduleConfigUpdate(BaseModel):
    trigger_type: Literal["interval", "cron"] | None = None
    trigger_config: str | None = None
    is_active: bool | None = None


class ScheduleConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    trigger_type: str
    trigger_config: str
    is_active: bool
    updated_at: datetime

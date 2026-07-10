from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: int
    category: str
    name: str
    intro: str | None
    description: str | None
    latitude: float | None
    longitude: float | None
    facility_type: str | None
    updated_at: datetime


class OperatingHoursSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section_title: str
    content_html: str
    display_order: int
    collected_at: datetime


class AmusementRideCreate(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    is_active: bool = True


class AmusementRideUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    is_active: bool | None = None


class AmusementRideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    location: str | None
    is_active: bool
    updated_at: datetime

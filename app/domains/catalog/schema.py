from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    msg_seq: int
    category: str
    name: str
    scientific_name: str | None
    english_name: str | None
    classification: str | None
    distribution: str | None
    diet: str | None
    registered_date: str | None
    thumbnail_url: str | None
    location_name: str | None
    source_url: str
    updated_at: datetime


class PlantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    msg_seq: int
    category: str
    name: str
    description: str | None
    registered_date: str | None
    thumbnail_url: str | None
    source_url: str
    updated_at: datetime

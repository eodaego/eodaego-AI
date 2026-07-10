from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.facility.model import Facility


def list_facilities(db: Session) -> list[Facility]:
    return list(db.scalars(select(Facility)).all())

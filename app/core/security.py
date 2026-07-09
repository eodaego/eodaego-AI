from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def verify_internal_api_key(x_internal_api_key: str = Header(...)) -> None:
    settings = get_settings()
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal api key"
        )

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    internal_api_key: str
    database_url: str

    model_config = SettingsConfigDict(env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "local")
    return Settings(_env_file=f".env.{app_env}")  # type: ignore[call-arg]

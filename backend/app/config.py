"""Settings from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Realtime Monitoring API"
    fleet_size: int = Field(default=6, ge=0, le=200)
    fleet_seed: int = 42
    collect_interval_seconds: float = Field(default=2.0, gt=0)
    ring_capacity: int = Field(default=1800, ge=10)
    sqlite_path: str | None = None
    host_collector_enabled: bool = True
    collector_enabled: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split(cls, v: object) -> object:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("sqlite_path", mode="before")
    @classmethod
    def _empty_is_none(cls, v: object) -> object:
        return None if v == "" else v


@lru_cache
def get_settings() -> Settings:
    return Settings()

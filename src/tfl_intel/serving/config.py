"""Configuration for the FastAPI serving layer."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServingSettings(BaseSettings):
    """Runtime settings for read-only DuckDB API serving."""

    duckdb_path: str = Field(default="/data/tfl_intel.duckdb", alias="DUCKDB_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


def load_settings() -> ServingSettings:
    """Load serving settings fresh from environment and optional .env file."""

    return ServingSettings()


@lru_cache
def get_settings() -> ServingSettings:
    """Return process-wide cached serving settings.

    Request handlers should use this instead of load_settings so each
    request does not re-read .env from disk. Tests that change DUCKDB_PATH
    must call get_settings.cache_clear().
    """

    return load_settings()

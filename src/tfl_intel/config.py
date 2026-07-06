"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for local ingestion and future pipeline components."""

    tfl_api_base_url: str = Field(
        default="https://api.tfl.gov.uk/Line", alias="TFL_API_BASE_URL"
    )
    tfl_app_key: str | None = Field(default=None, alias="TFL_APP_KEY")
    database_url: str = Field(
        default="postgresql://tfl_intel:tfl_intel@localhost:5432/tfl_intel",
        alias="DATABASE_URL",
    )
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="tfl_intel", alias="POSTGRES_DB")
    postgres_user: str = Field(default="tfl_intel", alias="POSTGRES_USER")
    postgres_password: str = Field(default="tfl_intel", alias="POSTGRES_PASSWORD")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


def load_settings() -> Settings:
    """Load settings from environment variables and optional local .env file."""

    return Settings()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for modules that need process-wide configuration."""

    return load_settings()

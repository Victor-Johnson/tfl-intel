from tfl_intel.config import Settings


def test_config_loads_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.tfl_api_base_url == "https://api.tfl.gov.uk/Line"
    assert (
        settings.database_url
        == "postgresql://tfl_intel:tfl_intel@localhost:5432/tfl_intel"
    )
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.log_level == "INFO"


def test_config_loads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TFL_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.test/db")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.tfl_api_base_url == "https://example.test"
    assert settings.database_url == "postgresql://example.test/db"
    assert settings.postgres_port == 15432
    assert settings.log_level == "DEBUG"

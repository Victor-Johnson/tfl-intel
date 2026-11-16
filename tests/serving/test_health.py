import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from tfl_intel.serving.routers import health


@pytest.mark.anyio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "tfl-intel-serving"}


@pytest.mark.anyio
async def test_ready_returns_structured_response(client: AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["duckdb_file_exists"] is True
    assert payload["checks"]["analytics_tables_exist"] is True
    assert payload["missing_tables"] == []


@pytest.mark.anyio
async def test_ready_returns_503_when_analytics_are_missing(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "check_required_tables", lambda: (False, ["missing"]))

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"

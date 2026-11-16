import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_root_redirects_to_dashboard(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


@pytest.mark.anyio
async def test_dashboard_is_served(client: AsyncClient) -> None:
    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert "TfL Reliability Intelligence" in response.text
    assert "/api/v1/lines/reliability" in response.text
    assert "/api/v1/network/status-mix" in response.text
    assert "/api/v1/network/disruption-heatmap" in response.text
    assert "Coverage vs observed uptime" in response.text
    assert "Mode comparison" in response.text
    assert "https://tfl-bi.victorjohnson.dev" in response.text
    assert "/reliability/daily?days=" in response.text
    assert "Daily reliability trend" in response.text
    assert "Pipeline warning" in response.text
    assert "Data provided by Transport for London" in response.text
    assert "Unofficial portfolio project" in response.text

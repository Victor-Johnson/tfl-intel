import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from tfl_intel.serving.config import get_settings


@pytest.mark.anyio
async def test_root_redirects_to_dashboard(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


@pytest.mark.anyio
async def test_dashboard_is_served(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("BI_DASHBOARD_URL", "")
    get_settings.cache_clear()
    response = await client.get("/dashboard")

    assert response.status_code == 200
    assert "TfL Reliability Intelligence" in response.text
    assert "/api/v1/lines/reliability" in response.text
    assert "/api/v1/network/status-mix" in response.text
    assert "/api/v1/network/disruption-heatmap" in response.text
    assert "Coverage vs observed uptime" in response.text
    assert "Mode comparison" in response.text
    assert '<a class="bi-link"' not in response.text
    assert "/reliability/daily?days=" in response.text
    assert "Daily reliability trend" in response.text
    assert "Pipeline warning" in response.text
    assert "Data provided by Transport for London" in response.text
    assert "Unofficial portfolio project" in response.text


@pytest.mark.anyio
async def test_dashboard_links_to_labelled_local_bi_demo(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("BI_DASHBOARD_URL", "http://127.0.0.1:3001/dashboard/1")
    monkeypatch.setenv("BI_DASHBOARD_DEMO", "true")
    get_settings.cache_clear()

    response = await client.get("/dashboard")

    assert 'href="http://127.0.0.1:3001/dashboard/1"' in response.text
    assert "Open BI demo (fixture data)" in response.text


@pytest.mark.anyio
async def test_dashboard_links_to_vetted_https_bi_workspace(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "BI_DASHBOARD_URL", "https://tfl-bi.victorjohnson.dev/dashboard/1"
    )
    monkeypatch.setenv("BI_DASHBOARD_DEMO", "false")
    get_settings.cache_clear()

    response = await client.get("/dashboard")

    assert 'href="https://tfl-bi.victorjohnson.dev/dashboard/1"' in response.text
    assert "Open BI workspace" in response.text
    assert "fixture data" not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "http://example.com/dashboard/1",
        "https://u:p@example.com",
    ],
)
async def test_dashboard_hides_unsafe_bi_url(
    client: AsyncClient, monkeypatch: MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("BI_DASHBOARD_URL", url)
    get_settings.cache_clear()

    response = await client.get("/dashboard")

    assert '<a class="bi-link"' not in response.text

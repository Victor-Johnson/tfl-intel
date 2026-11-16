import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_reliability_leaderboard_returns_latest_window(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/lines/reliability")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["line_id"] == "central"
    assert payload[0]["observed_uptime_pct"] == 87.09
    assert payload[0]["coverage_quality"] == "insufficient"
    assert payload[0]["reliability_rank"] == 1


@pytest.mark.anyio
async def test_reliability_leaderboard_filters_by_coverage(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/lines/reliability?min_coverage_pct=80")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_reliability_leaderboard_filters_by_mode(client: AsyncClient) -> None:
    response = await client.get("/api/v1/lines/reliability?mode_name=tram")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_daily_reliability_respects_days_limit(client: AsyncClient) -> None:
    response = await client.get("/api/v1/lines/central/reliability/daily?days=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["service_date"] == "2026-07-06"
    assert payload[0]["observed_uptime_pct"] == 75.0


@pytest.mark.anyio
async def test_daily_reliability_returns_404_for_unknown_line(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/lines/unknown/reliability/daily")

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown line: unknown"


@pytest.mark.anyio
async def test_daily_reliability_rejects_invalid_days(client: AsyncClient) -> None:
    response = await client.get("/api/v1/lines/central/reliability/daily?days=0")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_disruptions_support_filters(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/disruptions?line_id=central&resolved=true&limit=10"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["disruption_event_id"] == "event-1"
    assert payload[0]["is_resolved"] is True


@pytest.mark.anyio
async def test_network_reliability_groups_by_mode(client: AsyncClient) -> None:
    response = await client.get("/api/v1/network/reliability-by-mode?days=30")

    assert response.status_code == 200
    assert response.json() == [
        {
            "mode_name": "tube",
            "line_count": 1,
            "total_observations": 488,
            "disrupted_observations": 63,
            "observed_uptime_pct": 87.09,
            "average_coverage_pct": 84.72,
            "disruption_event_count": 3,
            "mean_recovery_minutes": 27.5,
            "first_service_date": "2026-07-05",
            "last_service_date": "2026-07-06",
        }
    ]


@pytest.mark.anyio
async def test_network_status_mix_aggregates_recent_window(client: AsyncClient) -> None:
    response = await client.get("/api/v1/network/status-mix?days=30&mode_name=tube")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0] == {
        "mode_name": "tube",
        "status_description": "Good Service",
        "is_disrupted": False,
        "observation_count": 425,
        "observation_pct": 87.09,
    }
    assert payload[1]["observation_count"] == 63
    assert payload[1]["observation_pct"] == 12.91


@pytest.mark.anyio
async def test_network_disruption_heatmap_returns_hourly_rates(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/network/disruption-heatmap?days=30")

    assert response.status_code == 200
    payload = response.json()
    assert [
        (row["weekday_name"], row["hour_of_day"], row["disruption_pct"])
        for row in payload
    ] == [
        ("Sun", 8, 0.0),
        ("Mon", 8, 25.0),
        ("Mon", 9, 10.0),
    ]


@pytest.mark.anyio
async def test_network_analytics_reject_invalid_window(client: AsyncClient) -> None:
    response = await client.get("/api/v1/network/status-mix?days=0")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_disruptions_reject_invalid_limit(client: AsyncClient) -> None:
    response = await client.get("/api/v1/disruptions?limit=501")

    assert response.status_code == 422

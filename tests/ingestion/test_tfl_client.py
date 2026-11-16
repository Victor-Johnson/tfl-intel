from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import pytest
import respx
from httpx import Response

from tfl_intel.config import Settings
from tfl_intel.ingestion.clients.tfl_client import TfLLineClient


def test_client_calls_correct_path_for_line_status_by_mode() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(200, json=[])
        )

        assert TfLLineClient(settings).get_line_status_by_mode("tube") == []

    assert route.called


def test_client_includes_app_key_when_configured() -> None:
    settings = Settings(
        tfl_api_base_url="https://api.example.test/Line",
        tfl_app_key="secret-test-key",
    )

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(200, json=[])
        )

        TfLLineClient(settings).get_line_status_by_mode("tube")

    assert route.calls.last.request.url.params["app_key"] == "secret-test-key"


def test_client_raises_for_non_200_response() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        router.get("/Line/Mode/tube/Status").mock(return_value=Response(503))

        with pytest.raises(RuntimeError, match="HTTP 503"):
            TfLLineClient(settings).get_line_status_by_mode("tube")


def test_client_retries_server_errors_then_succeeds() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status")
        route.side_effect = [
            Response(500),
            Response(200, json=[{"id": "victoria"}]),
        ]

        payload = TfLLineClient(settings).get_line_status_by_mode("tube")

    assert payload == [{"id": "victoria"}]
    assert route.call_count == 2


def test_client_does_not_retry_client_errors() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status").mock(return_value=Response(404))

        with pytest.raises(RuntimeError, match="HTTP 404"):
            TfLLineClient(settings).get_line_status_by_mode("tube")

    assert route.call_count == 1


def test_client_retries_429_then_succeeds() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status")
        route.side_effect = [
            Response(429, headers={"Retry-After": "0"}),
            Response(200, json=[{"id": "victoria"}]),
        ]
        payload = TfLLineClient(settings).get_line_status_by_mode("tube")

    assert payload == [{"id": "victoria"}]
    assert route.call_count == 2


def test_retry_after_is_bounded_and_invalid_value_falls_back() -> None:
    from tfl_intel.ingestion.clients.tfl_client import _wait_for_retry

    def state(header: str | None) -> SimpleNamespace:
        request = httpx.Request("GET", "https://api.example.test")
        headers = {"Retry-After": header} if header is not None else {}
        response = Response(429, headers=headers, request=request)
        exc = httpx.HTTPStatusError("rate limited", request=request, response=response)
        return SimpleNamespace(
            attempt_number=1,
            outcome=SimpleNamespace(exception=lambda: exc),
        )

    assert _wait_for_retry(state("2")) == 2
    assert _wait_for_retry(state("999")) == 8
    assert _wait_for_retry(state("bad")) == 0.5
    assert _wait_for_retry(state(None)) == 0.5
    retry_at = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
    assert _wait_for_retry(state(retry_at)) == 8


def test_client_stops_after_three_429_responses() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(429, headers={"Retry-After": "0"})
        )
        with pytest.raises(RuntimeError, match="HTTP 429"):
            TfLLineClient(settings).get_line_status_by_mode("tube")

    assert route.call_count == 3


def test_client_stops_after_three_timeouts() -> None:
    settings = Settings(tfl_api_base_url="https://api.example.test/Line")

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status")
        route.side_effect = httpx.ReadTimeout("synthetic timeout")
        with pytest.raises(RuntimeError, match="timed out"):
            TfLLineClient(settings).get_line_status_by_mode("tube")

    assert route.call_count == 3

from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any

import pytest
import respx
from httpx import Response
from pytest import MonkeyPatch

from tfl_intel.config import Settings
from tfl_intel.ingestion.jobs import ingest_line_status


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ([], "no lines"),
        ([{"id": "central", "name": "Central", "lineStatuses": []}], "no statuses"),
        ([{"name": "Central", "lineStatuses": []}], "missing required line id"),
    ],
)
def test_invalid_poll_marks_run_failed(
    monkeypatch: MonkeyPatch, payload: list[dict[str, Any]], error: str
) -> None:
    calls: list[str] = []

    class Connection:
        def transaction(self) -> nullcontext[None]:
            return nullcontext()

        def close(self) -> None:
            calls.append("close")

    class Client:
        def __init__(self, _settings: object) -> None:
            pass

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def get_line_status_by_mode(self, _mode: str) -> list[dict[str, Any]]:
            return payload

    monkeypatch.setattr(ingest_line_status, "get_connection", Connection)
    monkeypatch.setattr(ingest_line_status, "TfLLineClient", Client)
    monkeypatch.setattr(
        ingest_line_status,
        "start_pipeline_run",
        lambda **_kwargs: calls.append("started"),
    )
    monkeypatch.setattr(
        ingest_line_status,
        "mark_pipeline_failed",
        lambda **_kwargs: calls.append("failed"),
    )
    monkeypatch.setattr(
        ingest_line_status,
        "mark_pipeline_success",
        lambda **_kwargs: calls.append("success"),
    )

    with pytest.raises(ValueError, match=error):
        ingest_line_status.run("tube")

    assert calls == ["started", "failed", "close"]


def test_exhausted_429_marks_run_failed(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    class Connection:
        def transaction(self) -> nullcontext[None]:
            return nullcontext()

        def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(ingest_line_status, "get_connection", Connection)
    monkeypatch.setattr(
        ingest_line_status,
        "load_settings",
        lambda: Settings(tfl_api_base_url="https://api.example.test/Line"),
    )
    monkeypatch.setattr(
        ingest_line_status,
        "start_pipeline_run",
        lambda **_kwargs: calls.append("started"),
    )
    monkeypatch.setattr(
        ingest_line_status,
        "mark_pipeline_failed",
        lambda **_kwargs: calls.append("failed"),
    )

    with respx.mock(base_url="https://api.example.test") as router:
        route = router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(429, headers={"Retry-After": "0"})
        )
        with pytest.raises(RuntimeError, match="HTTP 429"):
            ingest_line_status.run("tube")

    assert route.call_count == 3
    assert calls == ["started", "failed", "close"]


def test_source_timestamp_does_not_replace_poll_time(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class Connection:
        def transaction(self) -> nullcontext[None]:
            return nullcontext()

        def close(self) -> None:
            pass

    monkeypatch.setattr(ingest_line_status, "get_connection", Connection)
    monkeypatch.setattr(
        ingest_line_status,
        "load_settings",
        lambda: Settings(tfl_api_base_url="https://api.example.test/Line"),
    )
    monkeypatch.setattr(ingest_line_status, "start_pipeline_run", lambda **_: None)
    monkeypatch.setattr(ingest_line_status, "mark_pipeline_success", lambda **_: None)

    def capture_insert(**kwargs: Any) -> int:
        captured.update(kwargs)
        return 1

    monkeypatch.setattr(
        ingest_line_status, "insert_line_status_observations", capture_insert
    )
    old_time = "2026-01-01T12:00:00Z"
    payload = [
        {
            "id": "central",
            "name": "Central",
            "lineStatuses": [
                {
                    "statusSeverity": 9,
                    "statusSeverityDescription": "Minor Delays",
                    "modified": old_time,
                }
            ],
        }
    ]
    before = datetime.now(UTC)
    with respx.mock(base_url="https://api.example.test") as router:
        router.get("/Line/Mode/tube/Status").mock(
            return_value=Response(200, json=payload)
        )
        assert ingest_line_status.run("tube") == 1
    after = datetime.now(UTC)

    assert captured["observations"][0].status_modified == old_time
    assert before <= captured["observed_at"] <= after

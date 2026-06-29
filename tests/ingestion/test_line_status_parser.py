import json
from pathlib import Path
from typing import Any

import pytest

from tfl_intel.ingestion.parsers.line_status_parser import parse_line_status_response

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"


def _load_fixture(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_parser_handles_good_service_with_missing_reason() -> None:
    observations = parse_line_status_response(
        _load_fixture("line_status_good_service.json")
    )

    assert len(observations) == 1
    assert observations[0].line_id == "central"
    assert observations[0].line_name == "Central"
    assert observations[0].mode_name == "tube"
    assert observations[0].status_severity == 10
    assert observations[0].status_description == "Good Service"
    assert observations[0].reason is None
    assert observations[0].validity_start is None
    assert observations[0].validity_end is None
    assert observations[0].validity_is_now is None


def test_parser_handles_minor_delays_with_reason() -> None:
    observations = parse_line_status_response(
        _load_fixture("line_status_minor_delay.json")
    )

    assert len(observations) == 1
    assert observations[0].line_id == "district"
    assert observations[0].status_id == 1
    assert observations[0].status_severity == 9
    assert observations[0].status_description == "Minor Delays"
    assert observations[0].reason == "Synthetic signal failure at Example Road."
    assert observations[0].status_created == "2026-06-29T08:00:00Z"
    assert observations[0].status_modified == "2026-06-29T08:05:00Z"
    assert observations[0].validity_start == "2026-06-29T08:00:00Z"
    assert observations[0].validity_end == "2026-06-29T09:00:00Z"
    assert observations[0].validity_is_now is True


def test_parser_handles_one_line_with_multiple_line_statuses() -> None:
    observations = parse_line_status_response(
        [
            {
                "id": "jubilee",
                "name": "Jubilee",
                "modeName": "tube",
                "lineStatuses": [
                    {
                        "statusSeverity": 10,
                        "statusSeverityDescription": "Good Service",
                        "validityPeriods": [],
                    },
                    {
                        "statusSeverity": 9,
                        "statusSeverityDescription": "Minor Delays",
                        "reason": "Synthetic crowding.",
                        "validityPeriods": [
                            {
                                "fromDate": "2026-06-29T10:00:00Z",
                                "toDate": "2026-06-29T11:00:00Z",
                                "isNow": False,
                            }
                        ],
                    },
                ],
            }
        ]
    )

    assert len(observations) == 2
    assert [observation.status_description for observation in observations] == [
        "Good Service",
        "Minor Delays",
    ]
    assert observations[1].validity_start == "2026-06-29T10:00:00Z"
    assert observations[1].validity_is_now is False


def test_parser_handles_empty_line_statuses() -> None:
    observations = parse_line_status_response(
        [{"id": "jubilee", "name": "Jubilee", "lineStatuses": []}]
    )

    assert observations == []


def test_parser_raises_for_missing_line_id() -> None:
    with pytest.raises(ValueError, match="missing required line id or name"):
        parse_line_status_response([{"name": "Central", "lineStatuses": []}])


def test_parser_raises_for_missing_status_description() -> None:
    with pytest.raises(ValueError, match="missing statusSeverityDescription"):
        parse_line_status_response(
            [
                {
                    "id": "central",
                    "name": "Central",
                    "lineStatuses": [{"statusSeverity": 10}],
                }
            ]
        )

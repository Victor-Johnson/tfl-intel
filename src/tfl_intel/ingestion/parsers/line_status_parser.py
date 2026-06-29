"""Parse TfL Line/Status API responses into normalized observations."""

from typing import Any

from tfl_intel.ingestion.models.line_status import LineStatusObservation


def parse_line_status_response(
    payload: list[dict[str, Any]],
) -> list[LineStatusObservation]:
    """Parse a TfL Line/Status response.

    The output grain is one row per entry in each line's ``lineStatuses`` array.
    """

    observations: list[LineStatusObservation] = []
    for line in payload:
        line_id = line.get("id")
        line_name = line.get("name")
        if not line_id or not line_name:
            msg = "TfL line status item is missing required line id or name"
            raise ValueError(msg)

        line_statuses = line.get("lineStatuses") or []
        if not isinstance(line_statuses, list):
            msg = f"TfL line {line_id!r} has non-list lineStatuses"
            raise ValueError(msg)

        for status in line_statuses:
            if not isinstance(status, dict):
                msg = f"TfL line {line_id!r} contains a non-object status item"
                raise ValueError(msg)

            if status.get("statusSeverity") is None:
                msg = f"TfL line {line_id!r} status is missing statusSeverity"
                raise ValueError(msg)
            if not status.get("statusSeverityDescription"):
                msg = (
                    f"TfL line {line_id!r} status is missing statusSeverityDescription"
                )
                raise ValueError(msg)

            validity_start, validity_end, validity_is_now = _first_validity_period(
                status
            )
            observations.append(
                LineStatusObservation(
                    line_id=str(line_id),
                    line_name=str(line_name),
                    mode_name=_optional_str(line.get("modeName")),
                    status_id=status.get("id"),
                    status_severity=status["statusSeverity"],
                    status_description=str(status["statusSeverityDescription"]),
                    reason=status.get("reason"),
                    status_created=_optional_str(status.get("created")),
                    status_modified=_optional_str(status.get("modified")),
                    validity_start=validity_start,
                    validity_end=validity_end,
                    validity_is_now=validity_is_now,
                    raw_payload={"line": line, "line_status": status},
                )
            )

    return observations


def _first_validity_period(
    status: dict[str, Any],
) -> tuple[str | None, str | None, bool | None]:
    periods = status.get("validityPeriods") or []
    if not periods or not isinstance(periods, list) or not isinstance(periods[0], dict):
        return None, None, None

    first_period = periods[0]
    return (
        _optional_str(first_period.get("fromDate")),
        _optional_str(first_period.get("toDate")),
        first_period.get("isNow"),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)

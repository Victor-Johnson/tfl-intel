"""Models for parsed TfL line status observations."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class LineStatusObservation(BaseModel):
    """One parsed status observation emitted from a TfL line status item."""

    line_id: str
    line_name: str
    mode_name: str | None = None
    status_id: int | None = None
    status_severity: int
    status_description: str
    reason: str | None = None
    status_created: str | None = None
    status_modified: str | None = None
    validity_start: str | None = None
    validity_end: str | None = None
    validity_is_now: bool | None = None
    raw_payload: dict[str, Any]

    model_config = ConfigDict(extra="allow")

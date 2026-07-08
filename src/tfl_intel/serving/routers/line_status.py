"""Line status analytical routes."""

from fastapi import APIRouter, Query

from tfl_intel.serving.db import fetch_all
from tfl_intel.serving.schemas import (
    CurrentLineStatusResponse,
    LineStatusHistoryItem,
    LineStatusSummaryResponse,
)

router = APIRouter(prefix="/api/v1/lines", tags=["line-status"])


@router.get("/current-status", response_model=list[CurrentLineStatusResponse])
def current_status() -> list[dict]:
    """Return the latest observed status per TfL line."""

    return fetch_all(
        """
        SELECT
            line_id,
            line_name,
            status_description,
            status_severity,
            reason,
            observed_at,
            ingestion_run_id
        FROM analytics.current_line_status
        ORDER BY line_name
        """
    )


@router.get("/status-summary", response_model=list[LineStatusSummaryResponse])
def status_summary() -> list[dict]:
    """Return grouped observation counts by line and status."""

    return fetch_all(
        """
        SELECT
            line_id,
            line_name,
            status_description,
            status_severity,
            observation_count,
            first_observed_at,
            last_observed_at
        FROM analytics.line_status_summary
        ORDER BY line_name, status_severity DESC
        """
    )


@router.get("/{line_id}/history", response_model=list[LineStatusHistoryItem])
def line_history(
    line_id: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """Return recent raw status observations for one line."""

    return fetch_all(
        """
        SELECT
            observation_id,
            line_id,
            line_name,
            status_description,
            status_severity,
            reason,
            observed_at,
            ingestion_run_id
        FROM raw_snapshot.tfl_line_status_observations
        WHERE line_id = ?
        ORDER BY observed_at DESC, ingested_at DESC, observation_id DESC
        LIMIT ?
        """,
        (line_id, limit),
    )

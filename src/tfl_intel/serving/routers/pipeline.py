"""Pipeline health and freshness routes."""

from fastapi import APIRouter, HTTPException

from tfl_intel.serving.db import fetch_one
from tfl_intel.serving.schemas import (
    PipelineFreshnessResponse,
    PipelineLatestRunResponse,
)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("/latest-run", response_model=PipelineLatestRunResponse)
def latest_run() -> dict:
    """Return the latest pipeline run captured in the DuckDB snapshot."""

    row = fetch_one(
        """
        SELECT
            ingestion_run_id,
            status,
            started_at,
            finished_at,
            records_received,
            records_inserted
        FROM analytics.pipeline_freshness
        """
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return row


@router.get("/freshness", response_model=PipelineFreshnessResponse)
def freshness() -> dict:
    """Return latest run status and successful-run freshness."""

    row = fetch_one(
        """
        SELECT
            ingestion_run_id,
            status,
            started_at,
            finished_at,
            records_received,
            records_inserted,
            latest_success_finished_at,
            minutes_since_latest_success
        FROM analytics.pipeline_freshness
        """
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No pipeline freshness found")
    return row

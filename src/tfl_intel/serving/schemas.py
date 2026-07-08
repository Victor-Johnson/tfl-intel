"""Pydantic response models for the read-only serving API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadyResponse(BaseModel):
    status: str
    duckdb_path: str
    checks: dict[str, bool]
    missing_tables: list[str]


class CurrentLineStatusResponse(BaseModel):
    line_id: str
    line_name: str
    status_description: str
    status_severity: int
    reason: str | None = None
    observed_at: datetime
    ingestion_run_id: str


class LineStatusSummaryResponse(BaseModel):
    line_id: str
    line_name: str
    status_description: str
    status_severity: int
    observation_count: int
    first_observed_at: datetime
    last_observed_at: datetime


class LineStatusHistoryItem(BaseModel):
    observation_id: str
    line_id: str
    line_name: str
    status_description: str
    status_severity: int
    reason: str | None = None
    observed_at: datetime
    ingestion_run_id: str


class PipelineLatestRunResponse(BaseModel):
    ingestion_run_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    records_received: int
    records_inserted: int


class PipelineFreshnessResponse(PipelineLatestRunResponse):
    latest_success_finished_at: datetime | None = None
    minutes_since_latest_success: int | None = None

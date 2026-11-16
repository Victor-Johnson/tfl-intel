"""Pydantic response models for the read-only serving API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

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


CoverageQuality = Literal["insufficient", "provisional", "reliable"]


class LineReliabilityResponse(BaseModel):
    window_start_date: date
    window_end_date: date
    line_id: str
    line_name: str
    total_observations: int
    observed_minutes: int
    estimated_disruption_minutes: int
    disruption_event_count: int
    resolved_disruption_event_count: int
    observed_uptime_pct: float
    coverage_pct: float
    coverage_quality: CoverageQuality
    reliability_rank: int


class LineReliabilityDailyResponse(BaseModel):
    service_date: date
    line_id: str
    line_name: str
    total_observations: int
    good_service_observations: int
    disrupted_observations: int
    observed_minutes: int
    estimated_disruption_minutes: int
    observed_uptime_pct: float
    full_day_coverage_pct: float
    coverage_quality: CoverageQuality
    disruption_event_count: int
    resolved_disruption_event_count: int
    mean_recovery_minutes: float | None = None


class DisruptionEventResponse(BaseModel):
    disruption_event_id: str
    line_id: str
    line_name: str
    event_started_at: datetime
    event_ended_at: datetime | None = None
    event_duration_minutes: float | None = None
    observed_disruption_minutes: int
    worst_status_description: str
    latest_reason: str | None = None
    is_resolved: bool


class ModeReliabilitySummaryResponse(BaseModel):
    mode_name: str
    line_count: int
    total_observations: int
    disrupted_observations: int
    observed_uptime_pct: float
    average_coverage_pct: float
    disruption_event_count: int
    mean_recovery_minutes: float | None = None
    first_service_date: date
    last_service_date: date


class NetworkStatusMixResponse(BaseModel):
    mode_name: str
    status_description: str
    is_disrupted: bool
    observation_count: int
    observation_pct: float


class NetworkDisruptionHeatmapResponse(BaseModel):
    mode_name: str
    weekday_index: int
    weekday_name: str
    hour_of_day: int
    observation_count: int
    disrupted_observation_count: int
    disruption_pct: float

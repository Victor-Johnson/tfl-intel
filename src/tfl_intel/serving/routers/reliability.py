"""Reliability and disruption analytical routes."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from tfl_intel.serving.db import fetch_all, fetch_one
from tfl_intel.serving.schemas import (
    DisruptionEventResponse,
    LineReliabilityDailyResponse,
    LineReliabilityResponse,
    ModeReliabilitySummaryResponse,
    NetworkDisruptionHeatmapResponse,
    NetworkStatusMixResponse,
)

router = APIRouter(prefix="/api/v1", tags=["reliability"])


@router.get(
    "/lines/reliability",
    response_model=list[LineReliabilityResponse],
)
async def reliability_leaderboard(
    min_coverage_pct: float = Query(default=0.0, ge=0.0, le=100.0),
    mode_name: str | None = None,
) -> list[dict[str, object]]:
    """Return the latest seven-day line reliability leaderboard."""

    return fetch_all(
        """
        WITH filtered AS (
            SELECT
                window_start_date,
                window_end_date,
                line_id,
                line_name,
                total_observations_7d AS total_observations,
                observed_minutes_7d AS observed_minutes,
                estimated_disruption_minutes_7d
                    AS estimated_disruption_minutes,
                disruption_event_count_7d AS disruption_event_count,
                resolved_disruption_event_count_7d
                    AS resolved_disruption_event_count,
                observed_uptime_pct_7d AS observed_uptime_pct,
                coverage_pct_7d AS coverage_pct,
                coverage_quality_7d AS coverage_quality
            FROM analytics.line_reliability_rolling_7d
            WHERE window_end_date = (
                SELECT MAX(window_end_date)
                FROM analytics.line_reliability_rolling_7d
            )
              AND coverage_pct_7d >= ?
              AND (? IS NULL OR mode_name = ?)
        )
        SELECT
            *,
            ROW_NUMBER() OVER (
                ORDER BY observed_uptime_pct, line_name
            ) AS reliability_rank
        FROM filtered
        ORDER BY reliability_rank, line_name
        """,
        (min_coverage_pct, mode_name, mode_name),
    )


@router.get(
    "/lines/{line_id}/reliability/daily",
    response_model=list[LineReliabilityDailyResponse],
)
async def daily_line_reliability(
    line_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, object]]:
    """Return recent daily reliability metrics for one line."""

    line = fetch_one(
        "SELECT line_id FROM analytics.dim_line WHERE line_id = ?",
        (line_id,),
    )
    if line is None:
        raise HTTPException(status_code=404, detail=f"Unknown line: {line_id}")

    return fetch_all(
        """
        SELECT
            service_date,
            line_id,
            line_name,
            total_observations,
            good_service_observations,
            disrupted_observations,
            observed_minutes,
            estimated_disruption_minutes,
            observed_uptime_pct,
            full_day_coverage_pct,
            coverage_quality,
            disruption_event_count,
            resolved_disruption_event_count,
            mean_recovery_minutes
        FROM analytics.line_reliability_daily
        WHERE line_id = ?
        ORDER BY service_date DESC
        LIMIT ?
        """,
        (line_id, days),
    )


@router.get(
    "/disruptions",
    response_model=list[DisruptionEventResponse],
)
async def disruption_events(
    line_id: str | None = None,
    mode_name: str | None = None,
    resolved: bool | None = None,
    started_since: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    """Return disruption events with optional line, state, and date filters."""

    filters: list[str] = []
    params: list[object] = []
    if line_id is not None:
        filters.append("line_id = ?")
        params.append(line_id)
    if mode_name is not None:
        filters.append("mode_name = ?")
        params.append(mode_name)
    if resolved is not None:
        filters.append("is_resolved = ?")
        params.append(resolved)
    if started_since is not None:
        filters.append("CAST(event_started_at AS DATE) >= ?")
        params.append(started_since)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)
    return fetch_all(
        f"""
        SELECT
            disruption_event_id,
            line_id,
            line_name,
            event_started_at,
            event_ended_at,
            event_duration_minutes,
            observed_disruption_minutes,
            worst_status_description,
            latest_reason,
            is_resolved
        FROM analytics.disruption_events
        {where_clause}
        ORDER BY event_started_at DESC
        LIMIT ?
        """,
        params,
    )


@router.get(
    "/network/reliability-by-mode",
    response_model=list[ModeReliabilitySummaryResponse],
)
async def network_reliability_by_mode(
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict[str, object]]:
    """Return coverage-aware network reliability grouped by transport mode."""

    return fetch_all(
        """
        WITH latest AS (
            SELECT MAX(service_date) AS latest_date
            FROM analytics.line_reliability_daily
        ),
        filtered AS (
            SELECT daily.*
            FROM analytics.line_reliability_daily AS daily, latest
            WHERE daily.service_date
                >= latest.latest_date - CAST(? - 1 AS INTEGER)
        ),
        events AS (
            SELECT
                mode_name,
                SUM(disruption_event_count) AS disruption_event_count,
                AVG(mean_recovery_minutes) FILTER (
                    WHERE mean_recovery_minutes IS NOT NULL
                ) AS mean_recovery_minutes
            FROM filtered
            GROUP BY mode_name
        )
        SELECT
            filtered.mode_name,
            COUNT(DISTINCT filtered.line_id) AS line_count,
            SUM(filtered.total_observations) AS total_observations,
            SUM(filtered.disrupted_observations) AS disrupted_observations,
            ROUND(
                100.0 * SUM(filtered.good_service_observations)
                / NULLIF(SUM(filtered.total_observations), 0),
                2
            ) AS observed_uptime_pct,
            ROUND(AVG(filtered.full_day_coverage_pct), 2)
                AS average_coverage_pct,
            events.disruption_event_count,
            ROUND(events.mean_recovery_minutes, 2) AS mean_recovery_minutes,
            MIN(filtered.service_date) AS first_service_date,
            MAX(filtered.service_date) AS last_service_date
        FROM filtered
        JOIN events USING (mode_name)
        GROUP BY
            filtered.mode_name,
            events.disruption_event_count,
            events.mean_recovery_minutes
        ORDER BY filtered.mode_name
        """,
        (days,),
    )


@router.get(
    "/network/status-mix",
    response_model=list[NetworkStatusMixResponse],
)
async def network_status_mix(
    days: int = Query(default=30, ge=1, le=365),
    mode_name: str | None = None,
) -> list[dict[str, object]]:
    """Return the passenger-visible status distribution for a recent window."""

    return fetch_all(
        """
        WITH latest AS (
            SELECT MAX(service_date) AS latest_date
            FROM analytics.network_status_mix_daily
        ),
        aggregated AS (
            SELECT
                status_description,
                BOOL_OR(is_disrupted) AS is_disrupted,
                SUM(observation_count) AS observation_count
            FROM analytics.network_status_mix_daily, latest
            WHERE service_date >= latest.latest_date - CAST(? - 1 AS INTEGER)
              AND (? IS NULL OR mode_name = ?)
            GROUP BY status_description
        )
        SELECT
            COALESCE(?, 'all') AS mode_name,
            status_description,
            is_disrupted,
            observation_count,
            ROUND(
                100.0 * observation_count
                / NULLIF(SUM(observation_count) OVER (), 0),
                2
            ) AS observation_pct
        FROM aggregated
        ORDER BY observation_count DESC, status_description
        """,
        (days, mode_name, mode_name, mode_name),
    )


@router.get(
    "/network/disruption-heatmap",
    response_model=list[NetworkDisruptionHeatmapResponse],
)
async def network_disruption_heatmap(
    days: int = Query(default=30, ge=1, le=365),
    mode_name: str | None = None,
) -> list[dict[str, object]]:
    """Return disruption rates by weekday and hour for a recent window."""

    return fetch_all(
        """
        WITH latest AS (
            SELECT MAX(service_date) AS latest_date
            FROM analytics.network_disruption_hourly
        )
        SELECT
            COALESCE(?, 'all') AS mode_name,
            weekday_index,
            ANY_VALUE(weekday_name) AS weekday_name,
            hour_of_day,
            SUM(observation_count) AS observation_count,
            SUM(disrupted_observation_count) AS disrupted_observation_count,
            ROUND(
                100.0 * SUM(disrupted_observation_count)
                / NULLIF(SUM(observation_count), 0),
                2
            ) AS disruption_pct
        FROM analytics.network_disruption_hourly, latest
        WHERE service_date >= latest.latest_date - CAST(? - 1 AS INTEGER)
          AND (? IS NULL OR mode_name = ?)
        GROUP BY weekday_index, hour_of_day
        ORDER BY weekday_index, hour_of_day
        """,
        (mode_name, days, mode_name, mode_name),
    )

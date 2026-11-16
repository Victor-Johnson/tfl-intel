"""Validate live DuckDB mart invariants after each refresh."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence

import duckdb

REQUIRED_TABLES = (
    "analytics.current_line_status",
    "analytics.dim_line",
    "analytics.dim_status_severity",
    "analytics.disruption_events",
    "analytics.line_reliability_daily",
    "analytics.line_reliability_rolling_7d",
    "analytics.line_disruption_hourly",
    "analytics.line_status_summary",
    "analytics.network_disruption_hourly",
    "analytics.network_status_mix_daily",
    "analytics.pipeline_freshness",
    "intermediate.line_status_intervals",
    "intermediate.line_status_per_poll",
)

INVARIANT_QUERIES = {
    "duplicate_line_poll_buckets": """
        SELECT COUNT(*)
        FROM (
            SELECT line_id, observation_bucket
            FROM intermediate.line_status_per_poll
            GROUP BY line_id, observation_bucket
            HAVING COUNT(*) > 1
        )
    """,
    "invalid_daily_reliability": """
        SELECT COUNT(*)
        FROM analytics.line_reliability_daily
        WHERE observed_uptime_pct NOT BETWEEN 0 AND 100
           OR full_day_coverage_pct NOT BETWEEN 0 AND 100
           OR coverage_quality NOT IN (
               'insufficient', 'provisional', 'reliable'
           )
           OR good_service_observations + disrupted_observations
              <> total_observations
    """,
    "invalid_rolling_reliability": """
        SELECT COUNT(*)
        FROM analytics.line_reliability_rolling_7d
        WHERE observed_uptime_pct_7d NOT BETWEEN 0 AND 100
           OR coverage_pct_7d NOT BETWEEN 0 AND 100
           OR coverage_quality_7d NOT IN (
               'insufficient', 'provisional', 'reliable'
           )
    """,
    "negative_event_durations": """
        SELECT COUNT(*)
        FROM analytics.disruption_events
        WHERE event_duration_minutes < 0
    """,
    "invalid_network_status_mix": """
        SELECT COUNT(*)
        FROM analytics.network_status_mix_daily
        WHERE observation_count < 0
           OR mode_name IS NULL
           OR status_description IS NULL
    """,
    "invalid_network_heatmap": """
        SELECT COUNT(*)
        FROM analytics.network_disruption_hourly
        WHERE weekday_index NOT BETWEEN 0 AND 6
           OR hour_of_day NOT BETWEEN 0 AND 23
           OR disruption_pct NOT BETWEEN 0 AND 100
           OR disrupted_observation_count > observation_count
    """,
    "invalid_line_hourly_pattern": """
        SELECT COUNT(*)
        FROM analytics.line_disruption_hourly
        WHERE weekday_index NOT BETWEEN 0 AND 6
           OR hour_of_day NOT BETWEEN 0 AND 23
           OR observation_count <= 0
           OR disrupted_observation_count > observation_count
           OR observed_disruption_pct NOT BETWEEN 0 AND 100
    """,
    "missing_current_line_statuses": """
        SELECT COUNT(*)
        FROM analytics.dim_line AS line
        LEFT JOIN analytics.current_line_status AS status
            USING (line_id)
        WHERE line.last_observed_at IS NOT NULL
          AND status.line_id IS NULL
    """,
    "freshness_run_mismatch": """
        WITH raw_latest AS (
            SELECT ingestion_run_id
            FROM raw_snapshot.pipeline_runs
            ORDER BY started_at DESC, ingestion_run_id DESC
            LIMIT 1
        )
        SELECT COUNT(*)
        FROM raw_latest
        CROSS JOIN analytics.pipeline_freshness AS freshness
        WHERE raw_latest.ingestion_run_id <> freshness.ingestion_run_id
    """,
}


def validate_marts(duckdb_path: str) -> dict[str, int]:
    """Validate required tables and return measured invariant failures."""

    with duckdb.connect(duckdb_path, read_only=True) as conn:
        existing_rows = conn.execute(
            """
            SELECT table_schema || '.' || table_name
            FROM information_schema.tables
            WHERE table_schema IN ('analytics', 'intermediate')
            """
        ).fetchall()
        existing = {row[0] for row in existing_rows}
        missing = sorted(set(REQUIRED_TABLES) - existing)
        if missing:
            msg = f"Required DuckDB marts are missing: {', '.join(missing)}"
            raise RuntimeError(msg)

        results = {
            name: conn.execute(query).fetchone()[0]
            for name, query in INVARIANT_QUERIES.items()
        }
        freshness_limit = int(os.getenv("MAX_PIPELINE_FRESHNESS_MINUTES", "15"))
        freshness = conn.execute(
            """
            SELECT date_diff(
                'minute', latest_success_finished_at, current_timestamp
            )
            FROM analytics.pipeline_freshness
            """
        ).fetchone()
        results["stale_pipeline"] = int(
            freshness is None or freshness[0] is None or freshness[0] > freshness_limit
        )

    failures = {name: count for name, count in results.items() if count != 0}
    if failures:
        details = ", ".join(f"{name}={count}" for name, count in failures.items())
        msg = f"DuckDB mart validation failed: {details}"
        raise RuntimeError(msg)

    return results


def main(argv: Sequence[str] | None = None) -> None:
    """Run mart validation from the command line."""

    args = list(argv if argv is not None else sys.argv[1:])
    duckdb_path = (
        args[0] if args else os.getenv("DUCKDB_PATH", "/data/tfl_intel.duckdb")
    )
    results = validate_marts(duckdb_path)
    print(json.dumps({"status": "ok", "checks": results}, sort_keys=True))


if __name__ == "__main__":
    main()

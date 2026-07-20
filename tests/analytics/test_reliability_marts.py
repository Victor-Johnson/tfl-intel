"""Tests for the DuckDB reliability transformation layer."""

from pathlib import Path

import duckdb
import pytest

MARTS_DIR = Path("sql/duckdb/marts")
RELIABILITY_SQL_FILES = (
    "00_line_status_per_poll.sql",
    "05_dimensions.sql",
    "20_line_status_intervals.sql",
    "30_disruption_events.sql",
    "40_line_reliability_daily.sql",
    "50_line_reliability_rolling_7d.sql",
)


@pytest.fixture
def mart_connection() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA raw_snapshot")
    connection.execute("CREATE SCHEMA intermediate")
    connection.execute("CREATE SCHEMA analytics")
    connection.execute(
        """
        CREATE TABLE raw_snapshot.tfl_line_status_observations (
            observation_id VARCHAR NOT NULL,
            ingestion_run_id VARCHAR NOT NULL,
            line_id VARCHAR NOT NULL,
            line_name VARCHAR NOT NULL,
            mode_name VARCHAR,
            status_severity INTEGER NOT NULL,
            status_description VARCHAR NOT NULL,
            reason VARCHAR,
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE raw_snapshot.tfl_lines (
            line_id VARCHAR,
            line_name VARCHAR,
            mode_name VARCHAR,
            created_source_at TIMESTAMPTZ,
            modified_source_at TIMESTAMPTZ
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE raw_snapshot.tfl_status_severity_codes (
            severity_level INTEGER,
            mode_name VARCHAR,
            description VARCHAR,
            ingested_at TIMESTAMPTZ
        )
        """
    )
    connection.execute(
        """
        INSERT INTO raw_snapshot.tfl_line_status_observations VALUES
            ('central-1a', 'run-1', 'central', 'Central', 'tube', 10,
             'Good Service', NULL, '2026-07-14 00:01:00+00',
             '2026-07-14 00:01:01+00'),
            ('central-1b', 'run-1', 'central', 'Central', 'tube', 6,
             'Severe Delays', 'signal failure',
             '2026-07-14 00:01:00+00', '2026-07-14 00:01:01+00'),
            ('central-2', 'run-2', 'central', 'Central', 'tube', 9,
             'Minor Delays', 'recovering',
             '2026-07-14 00:02:00+00', '2026-07-14 00:02:01+00'),
            ('central-3', 'run-3', 'central', 'Central', 'tube', 10,
             'Good Service', NULL, '2026-07-14 00:06:00+00',
             '2026-07-14 00:06:01+00'),
            ('central-4', 'run-4', 'central', 'Central', 'tube', 20,
             'Service Closed', 'planned closure',
             '2026-07-14 00:11:00+00', '2026-07-14 00:11:01+00'),
            ('central-5', 'run-5', 'central', 'Central', 'tube', 10,
             'Good Service', NULL, '2026-07-14 00:16:00+00',
             '2026-07-14 00:16:01+00'),
            ('bakerloo-1a', 'run-1', 'bakerloo', 'Bakerloo', 'tube', 10,
             'Good Service', NULL, '2026-07-14 00:01:00+00',
             '2026-07-14 00:01:01+00'),
            ('bakerloo-1b', 'run-1', 'bakerloo', 'Bakerloo', 'tube', 6,
             'Severe Delays', 'train fault',
             '2026-07-14 00:01:00+00', '2026-07-14 00:01:01+00'),
            ('bakerloo-2', 'run-3', 'bakerloo', 'Bakerloo', 'tube', 10,
             'Good Service', NULL, '2026-07-14 00:06:00+00',
             '2026-07-14 00:06:01+00')
        """
    )

    for filename in RELIABILITY_SQL_FILES:
        sql = (MARTS_DIR / filename).read_text(encoding="utf-8")
        connection.execute(sql)

    yield connection
    connection.close()


def test_per_poll_grain_and_status_selection(
    mart_connection: duckdb.DuckDBPyConnection,
) -> None:
    duplicates = mart_connection.execute(
        """
        SELECT line_id, observation_bucket
        FROM intermediate.line_status_per_poll
        GROUP BY line_id, observation_bucket
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    assert duplicates == []

    central_first = mart_connection.execute(
        """
        SELECT status_description
        FROM intermediate.line_status_per_poll
        WHERE line_id = 'central'
        ORDER BY observation_bucket
        LIMIT 1
        """
    ).fetchone()
    assert central_first == ("Minor Delays",)

    bakerloo_first = mart_connection.execute(
        """
        SELECT status_description, source_status_count
        FROM intermediate.line_status_per_poll
        WHERE line_id = 'bakerloo'
        ORDER BY observation_bucket
        LIMIT 1
        """
    ).fetchone()
    assert bakerloo_first == ("Severe Delays", 2)


def test_daily_reliability_reconciles_observations(
    mart_connection: duckdb.DuckDBPyConnection,
) -> None:
    central = mart_connection.execute(
        """
        SELECT
            total_observations,
            good_service_observations,
            disrupted_observations,
            observed_uptime_pct,
            estimated_disruption_minutes,
            disruption_event_count,
            resolved_disruption_event_count
        FROM analytics.line_reliability_daily
        WHERE line_id = 'central'
        """
    ).fetchone()
    assert central == (4, 2, 2, 50.0, 10, 2, 2)


def test_dimensions_fall_back_to_observed_data(
    mart_connection: duckdb.DuckDBPyConnection,
) -> None:
    line = mart_connection.execute(
        """
        SELECT line_name, has_reference_metadata
        FROM analytics.dim_line
        WHERE line_id = 'central'
        """
    ).fetchone()
    assert line == ("Central", False)

    severity = mart_connection.execute(
        """
        SELECT description, is_disrupted, disruption_priority
        FROM analytics.dim_status_severity
        WHERE severity_level = 20
        """
    ).fetchone()
    assert severity == ("Service Closed", True, 100)


def test_disruption_events_resolve_on_good_service(
    mart_connection: duckdb.DuckDBPyConnection,
) -> None:
    events = mart_connection.execute(
        """
        SELECT worst_status_description, is_resolved
        FROM analytics.disruption_events
        WHERE line_id = 'central'
        ORDER BY event_started_at
        """
    ).fetchall()
    assert events == [("Minor Delays", True), ("Service Closed", True)]


def test_reliability_percentages_are_bounded(
    mart_connection: duckdb.DuckDBPyConnection,
) -> None:
    invalid_daily_rows = mart_connection.execute(
        """
        SELECT COUNT(*)
        FROM analytics.line_reliability_daily
        WHERE observed_uptime_pct NOT BETWEEN 0 AND 100
           OR full_day_coverage_pct NOT BETWEEN 0 AND 100
           OR good_service_observations + disrupted_observations
              <> total_observations
        """
    ).fetchone()
    assert invalid_daily_rows == (0,)

    invalid_rolling_rows = mart_connection.execute(
        """
        SELECT COUNT(*)
        FROM analytics.line_reliability_rolling_7d
        WHERE observed_uptime_pct_7d NOT BETWEEN 0 AND 100
           OR coverage_pct_7d NOT BETWEEN 0 AND 100
        """
    ).fetchone()
    assert invalid_rolling_rows == (0,)

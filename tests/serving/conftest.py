from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from tfl_intel.serving.app import app
from tfl_intel.serving.config import get_settings


@pytest.fixture
def test_duckdb_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    db_path = tmp_path / "tfl_intel_test.duckdb"

    with duckdb.connect(str(db_path)) as conn:
        conn.execute("CREATE SCHEMA raw_snapshot")
        conn.execute("CREATE SCHEMA analytics")
        conn.execute(
            """
            CREATE TABLE raw_snapshot.tfl_line_status_observations (
                observation_id TEXT,
                line_id TEXT,
                line_name TEXT,
                status_description TEXT,
                status_severity INTEGER,
                reason TEXT,
                observed_at TIMESTAMP,
                ingested_at TIMESTAMP,
                ingestion_run_id TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO raw_snapshot.tfl_line_status_observations VALUES
            (
                'obs-2',
                'central',
                'Central',
                'Minor Delays',
                9,
                'Synthetic signal failure.',
                TIMESTAMP '2026-07-06 10:05:00',
                TIMESTAMP '2026-07-06 10:05:10',
                'run-2'
            ),
            (
                'obs-1',
                'central',
                'Central',
                'Good Service',
                10,
                NULL,
                TIMESTAMP '2026-07-06 10:00:00',
                TIMESTAMP '2026-07-06 10:00:10',
                'run-1'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.current_line_status AS
            SELECT
                line_id,
                line_name,
                status_description,
                status_severity,
                reason,
                observed_at,
                ingestion_run_id
            FROM raw_snapshot.tfl_line_status_observations
            WHERE observation_id = 'obs-2'
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.line_status_summary AS
            SELECT
                line_id,
                line_name,
                status_description,
                status_severity,
                COUNT(*) AS observation_count,
                MIN(observed_at) AS first_observed_at,
                MAX(observed_at) AS last_observed_at
            FROM raw_snapshot.tfl_line_status_observations
            GROUP BY
                line_id,
                line_name,
                status_description,
                status_severity
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.pipeline_freshness (
                ingestion_run_id TEXT,
                status TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                records_received INTEGER,
                records_inserted INTEGER,
                latest_success_finished_at TIMESTAMP,
                minutes_since_latest_success INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analytics.pipeline_freshness VALUES (
                'run-2',
                'success',
                TIMESTAMP '2026-07-06 10:05:00',
                TIMESTAMP '2026-07-06 10:05:20',
                11,
                11,
                TIMESTAMP '2026-07-06 10:05:20',
                4
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.dim_line AS
            SELECT DISTINCT
                line_id,
                line_name,
                'tube' AS mode_name,
                NULL::TIMESTAMP AS created_source_at,
                NULL::TIMESTAMP AS modified_source_at,
                MIN(observed_at) OVER () AS first_observed_at,
                MAX(observed_at) OVER () AS last_observed_at,
                FALSE AS has_reference_metadata
            FROM raw_snapshot.tfl_line_status_observations
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.dim_status_severity (
                severity_level INTEGER,
                description TEXT,
                mode_name TEXT,
                is_disrupted BOOLEAN,
                disruption_priority INTEGER,
                first_observed_at TIMESTAMP,
                last_observed_at TIMESTAMP,
                reference_ingested_at TIMESTAMP,
                has_reference_metadata BOOLEAN
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analytics.dim_status_severity VALUES
                (10, 'Good Service', 'tube', FALSE, 0,
                 TIMESTAMP '2026-07-06 10:00:00',
                 TIMESTAMP '2026-07-06 10:05:00', NULL, FALSE),
                (9, 'Minor Delays', 'tube', TRUE, 70,
                 TIMESTAMP '2026-07-06 10:00:00',
                 TIMESTAMP '2026-07-06 10:05:00', NULL, FALSE)
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.line_reliability_daily (
                service_date DATE,
                line_id TEXT,
                line_name TEXT,
                total_observations INTEGER,
                good_service_observations INTEGER,
                disrupted_observations INTEGER,
                observed_minutes INTEGER,
                estimated_disruption_minutes INTEGER,
                observed_uptime_pct DOUBLE,
                full_day_coverage_pct DOUBLE,
                coverage_quality TEXT,
                disruption_event_count INTEGER,
                resolved_disruption_event_count INTEGER,
                mean_recovery_minutes DOUBLE
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analytics.line_reliability_daily VALUES
                (DATE '2026-07-06', 'central', 'Central', 200, 150, 50,
                 1000, 250, 75.0, 69.44, 'insufficient', 2, 1, 35.0),
                (DATE '2026-07-05', 'central', 'Central', 288, 275, 13,
                 1440, 65, 95.49, 100.0, 'reliable', 1, 1, 20.0)
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.line_reliability_rolling_7d (
                window_end_date DATE,
                window_start_date DATE,
                line_id TEXT,
                line_name TEXT,
                total_observations_7d INTEGER,
                good_service_observations_7d INTEGER,
                disrupted_observations_7d INTEGER,
                observed_minutes_7d INTEGER,
                estimated_disruption_minutes_7d INTEGER,
                disruption_event_count_7d INTEGER,
                resolved_disruption_event_count_7d INTEGER,
                observed_uptime_pct_7d DOUBLE,
                coverage_pct_7d DOUBLE,
                coverage_quality_7d TEXT,
                least_reliable_rank_7d INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analytics.line_reliability_rolling_7d VALUES (
                DATE '2026-07-06', DATE '2026-06-30', 'central', 'Central',
                488, 425, 63, 2440, 315, 3, 2, 87.09, 24.21,
                'insufficient', 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE analytics.disruption_events (
                disruption_event_id TEXT,
                line_id TEXT,
                line_name TEXT,
                event_started_at TIMESTAMP,
                event_ended_at TIMESTAMP,
                event_duration_minutes DOUBLE,
                observation_count INTEGER,
                observed_disruption_minutes INTEGER,
                worst_status_description TEXT,
                worst_disruption_priority INTEGER,
                latest_reason TEXT,
                is_resolved BOOLEAN
            )
            """
        )
        conn.execute(
            """
            INSERT INTO analytics.disruption_events VALUES (
                'event-1', 'central', 'Central',
                TIMESTAMP '2026-07-06 10:05:00',
                TIMESTAMP '2026-07-06 10:40:00', 35.0, 7, 35,
                'Minor Delays', 70, 'Synthetic signal failure.', TRUE
            )
            """
        )

    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    get_settings.cache_clear()
    yield db_path
    get_settings.cache_clear()


@pytest.fixture
def client(test_duckdb_path: Path) -> TestClient:
    return TestClient(app)

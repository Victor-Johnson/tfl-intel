from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from tfl_intel.serving.app import app


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

    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    yield db_path


@pytest.fixture
def client(test_duckdb_path: Path) -> TestClient:
    return TestClient(app)

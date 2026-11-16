"""Create a deterministic raw-snapshot DuckDB fixture for dbt CI builds."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb


def create_fixture(path: Path) -> None:
    """Create a small but complete raw_snapshot schema at ``path``."""

    path.unlink(missing_ok=True)
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE SCHEMA raw_snapshot")
        conn.execute(
            """
            CREATE TABLE raw_snapshot.pipeline_runs (
                ingestion_run_id VARCHAR,
                source_name VARCHAR,
                source_endpoint VARCHAR,
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                status VARCHAR,
                records_received INTEGER,
                records_inserted INTEGER,
                records_rejected INTEGER,
                error_message VARCHAR
            );
            INSERT INTO raw_snapshot.pipeline_runs VALUES (
                'run-1', 'tfl_line_status', '/Mode/tube/Status',
                TIMESTAMPTZ '2026-07-14 00:00:00+00',
                TIMESTAMPTZ '2026-07-14 00:00:02+00',
                'success', 2, 2, 0, NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE raw_snapshot.tfl_line_status_observations (
                observation_id VARCHAR,
                ingestion_run_id VARCHAR,
                line_id VARCHAR,
                line_name VARCHAR,
                mode_name VARCHAR,
                status_severity INTEGER,
                status_description VARCHAR,
                reason VARCHAR,
                observed_at TIMESTAMPTZ,
                ingested_at TIMESTAMPTZ
            );
            INSERT INTO raw_snapshot.tfl_line_status_observations VALUES
                ('central-1', 'run-1', 'central', 'Central', 'tube', 9,
                 'Minor Delays', 'Synthetic signal failure',
                 TIMESTAMPTZ '2026-07-14 00:01:00+00',
                 TIMESTAMPTZ '2026-07-14 00:01:01+00'),
                ('central-2', 'run-2', 'central', 'Central', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 00:06:00+00',
                 TIMESTAMPTZ '2026-07-14 00:06:01+00'),
                ('bakerloo-1', 'run-1', 'bakerloo', 'Bakerloo', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 00:01:00+00',
                 TIMESTAMPTZ '2026-07-14 00:01:01+00'),
                ('bakerloo-2', 'run-2', 'bakerloo', 'Bakerloo', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 00:06:00+00',
                 TIMESTAMPTZ '2026-07-14 00:06:01+00'),
                ('dst-spring', 'run-spring', 'dst-test', 'DST Test', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-03-29 00:05:00+00',
                 TIMESTAMPTZ '2026-03-29 00:05:01+00'),
                ('dst-autumn', 'run-autumn', 'dst-test', 'DST Test', 'tube', 9,
                 'Minor Delays', 'Synthetic DST fixture',
                 TIMESTAMPTZ '2026-10-25 00:05:00+00',
                 TIMESTAMPTZ '2026-10-25 00:05:01+00'),
                ('timeline-1', 'timeline-a', 'timeline', 'Timeline', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 10:00:00+00',
                 TIMESTAMPTZ '2026-07-14 10:00:01+00'),
                ('timeline-2', 'timeline-b', 'timeline', 'Timeline', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 10:05:00+00',
                 TIMESTAMPTZ '2026-07-14 10:05:01+00'),
                ('timeline-3', 'timeline-b', 'timeline', 'Timeline', 'tube', 9,
                 'Minor Delays', 'Synthetic delay',
                 TIMESTAMPTZ '2026-07-14 10:05:00+00',
                 TIMESTAMPTZ '2026-07-14 10:05:01+00'),
                ('timeline-4', 'timeline-c', 'timeline', 'Timeline', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 10:20:00+00',
                 TIMESTAMPTZ '2026-07-14 10:20:01+00'),
                ('timeline-5', 'timeline-d', 'timeline', 'Timeline', 'tube', 9,
                 'Minor Delays', 'Synthetic delay',
                 TIMESTAMPTZ '2026-07-14 10:20:30+00',
                 TIMESTAMPTZ '2026-07-14 10:20:31+00'),
                ('timeline-6', 'timeline-e', 'timeline', 'Timeline', 'tube', 10,
                 'Good Service', NULL,
                 TIMESTAMPTZ '2026-07-14 10:25:00+00',
                 TIMESTAMPTZ '2026-07-14 10:25:01+00');
            """
        )
        conn.execute(
            """
            CREATE TABLE raw_snapshot.tfl_lines (
                line_id VARCHAR,
                line_name VARCHAR,
                mode_name VARCHAR,
                created_source_at TIMESTAMPTZ,
                modified_source_at TIMESTAMPTZ,
                source_endpoint VARCHAR,
                ingested_at TIMESTAMPTZ
            );
            INSERT INTO raw_snapshot.tfl_lines VALUES
                ('central', 'Central', 'tube', NULL, NULL, '/Mode/tube',
                 TIMESTAMPTZ '2026-07-14 00:00:00+00'),
                ('bakerloo', 'Bakerloo', 'tube', NULL, NULL, '/Mode/tube',
                 TIMESTAMPTZ '2026-07-14 00:00:00+00');
            """
        )
        conn.execute(
            """
            CREATE TABLE raw_snapshot.tfl_status_severity_codes (
                severity_level INTEGER,
                mode_name VARCHAR,
                description VARCHAR,
                source_endpoint VARCHAR,
                ingested_at TIMESTAMPTZ
            );
            INSERT INTO raw_snapshot.tfl_status_severity_codes VALUES
                (9, 'tube', 'Minor Delays', '/Meta/Severity',
                 TIMESTAMPTZ '2026-07-14 00:00:00+00'),
                (10, 'tube', 'Good Service', '/Meta/Severity',
                 TIMESTAMPTZ '2026-07-14 00:00:00+00');
            """
        )


def main() -> None:
    """Create the fixture at the supplied path."""

    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_dbt_ci_fixture.py PATH")
    create_fixture(Path(sys.argv[1]))


if __name__ == "__main__":
    main()

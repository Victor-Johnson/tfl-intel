-- Refresh the DuckDB analytical read model from Postgres raw tables.
-- Connection details come from libpq environment variables:
-- PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD.

INSTALL postgres;
LOAD postgres;

ATTACH '' AS pg_db (TYPE postgres, READ_ONLY);

CREATE SCHEMA IF NOT EXISTS raw_snapshot;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Raw snapshots keep Postgres as the source of truth while giving DuckDB a
-- local analytical copy for fast read-only.
CREATE OR REPLACE TABLE raw_snapshot.pipeline_runs AS
SELECT * FROM pg_db.raw.pipeline_runs;

CREATE OR REPLACE TABLE raw_snapshot.tfl_line_status_observations AS
SELECT * FROM pg_db.raw.tfl_line_status_observations;

CREATE OR REPLACE TABLE raw_snapshot.tfl_lines AS
SELECT * FROM pg_db.raw.tfl_lines;

CREATE OR REPLACE TABLE raw_snapshot.tfl_status_severity_codes AS
SELECT * FROM pg_db.raw.tfl_status_severity_codes;

CREATE OR REPLACE TABLE analytics.line_status_summary AS
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
ORDER BY
    line_name,
    status_severity DESC;

CREATE OR REPLACE TABLE analytics.current_line_status AS
SELECT
    line_id,
    line_name,
    status_description,
    status_severity,
    reason,
    observed_at,
    ingestion_run_id
FROM raw_snapshot.tfl_line_status_observations
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY line_id
    ORDER BY observed_at DESC, ingested_at DESC, observation_id DESC
) = 1
ORDER BY line_name;

CREATE OR REPLACE TABLE analytics.pipeline_freshness AS
WITH latest_run AS (
    SELECT
        ingestion_run_id,
        status,
        started_at,
        finished_at,
        records_received,
        records_inserted
    FROM raw_snapshot.pipeline_runs
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY started_at DESC, ingestion_run_id DESC
    ) = 1
),
latest_success AS (
    SELECT MAX(finished_at) AS latest_success_finished_at
    FROM raw_snapshot.pipeline_runs
    WHERE status = 'success'
)
SELECT
    latest_run.ingestion_run_id,
    latest_run.status,
    latest_run.started_at,
    latest_run.finished_at,
    latest_run.records_received,
    latest_run.records_inserted,
    latest_success.latest_success_finished_at,
    CASE
        WHEN latest_success.latest_success_finished_at IS NULL THEN NULL
        ELSE date_diff(
            'minute',
            latest_success.latest_success_finished_at,
            CURRENT_TIMESTAMP
        )
    END AS minutes_since_latest_success
FROM latest_run
CROSS JOIN latest_success;

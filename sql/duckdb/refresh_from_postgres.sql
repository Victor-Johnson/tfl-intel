-- Refresh the DuckDB raw snapshot from Postgres.
-- Connection details come from libpq environment variables:
-- PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD.

INSTALL postgres;
LOAD postgres;

ATTACH '' AS pg_db (TYPE postgres, READ_ONLY);

CREATE SCHEMA IF NOT EXISTS raw_snapshot;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Postgres remains the source of truth; these tables are disposable copies.
CREATE OR REPLACE TABLE raw_snapshot.pipeline_runs AS
SELECT * FROM pg_db.raw.pipeline_runs;

CREATE OR REPLACE TABLE raw_snapshot.tfl_line_status_observations AS
SELECT * FROM pg_db.raw.tfl_line_status_observations;

CREATE OR REPLACE TABLE raw_snapshot.tfl_lines AS
SELECT * FROM pg_db.raw.tfl_lines;

CREATE OR REPLACE TABLE raw_snapshot.tfl_status_severity_codes AS
SELECT * FROM pg_db.raw.tfl_status_severity_codes;

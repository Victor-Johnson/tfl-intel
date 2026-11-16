SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

DELETE FROM raw.tfl_line_status_observations
WHERE observed_at < now() - interval '90 days';

DELETE FROM raw.invalid_records
WHERE created_at < now() - interval '90 days';

DELETE FROM raw.pipeline_runs as runs
WHERE runs.started_at < now() - interval '90 days'
  AND NOT EXISTS (
      SELECT 1 FROM raw.tfl_line_status_observations as observations
      WHERE observations.ingestion_run_id = runs.ingestion_run_id
  )
  AND NOT EXISTS (
      SELECT 1 FROM raw.invalid_records as invalid
      WHERE invalid.ingestion_run_id = runs.ingestion_run_id
  );

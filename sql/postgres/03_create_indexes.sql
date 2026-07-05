--- Aim : To make queries faster to access 
CREATE INDEX IF NOT EXISTS idx_line_status_observed_at
ON raw.tfl_line_status_observations (observed_at);

CREATE INDEX IF NOT EXISTS idx_line_status_line_id
ON raw.tfl_line_status_observations (line_id);

CREATE INDEX IF NOT EXISTS idx_line_status_severity
ON raw.tfl_line_status_observations (status_severity);

CREATE INDEX IF NOT EXISTS idx_line_status_fingerprint
ON raw.tfl_line_status_observations (status_fingerprint);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
ON raw.pipeline_runs (started_at);
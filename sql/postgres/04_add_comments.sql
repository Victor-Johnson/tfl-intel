--- Database Documentation for detailed purpose 
COMMENT ON TABLE raw.tfl_line_status_observations IS
'Raw TfL Line API status observations. Grain: one row per line-status item per ingestion run.';

COMMENT ON COLUMN raw.tfl_line_status_observations.observation_id IS
'Deterministic unique ID for this line-status observation within a specific ingestion run.';

COMMENT ON COLUMN raw.tfl_line_status_observations.status_fingerprint IS
'Stable hash representing the underlying status content. Used to identify repeated status states across ingestion runs.';

COMMENT ON COLUMN raw.tfl_line_status_observations.raw_payload IS
'Original parsed TfL status payload preserved as JSONB for auditability and replay.';
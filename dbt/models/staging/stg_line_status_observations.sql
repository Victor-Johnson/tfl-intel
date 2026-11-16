select
    observation_id,
    ingestion_run_id,
    line_id,
    line_name,
    mode_name,
    status_severity,
    status_description,
    reason,
    observed_at,
    ingested_at
from {{ source('raw_snapshot', 'tfl_line_status_observations') }}

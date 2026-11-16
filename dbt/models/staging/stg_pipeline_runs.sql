select
    ingestion_run_id,
    source_name,
    source_endpoint,
    status,
    started_at,
    finished_at,
    records_received,
    records_inserted,
    records_rejected,
    error_message
from {{ source('raw_snapshot', 'pipeline_runs') }}

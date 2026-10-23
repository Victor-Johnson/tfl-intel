select
    line_id,
    line_name,
    mode_name,
    status_description,
    status_severity,
    reason,
    observed_at,
    ingestion_run_id
from {{ ref('int_line_status_per_poll') }}
qualify row_number() over (
    partition by line_id
    order by observed_at desc, ingested_at desc, observation_id desc
) = 1

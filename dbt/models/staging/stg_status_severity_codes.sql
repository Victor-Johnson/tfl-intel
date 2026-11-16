select
    severity_level,
    mode_name,
    description,
    source_endpoint,
    ingested_at
from {{ source('raw_snapshot', 'tfl_status_severity_codes') }}

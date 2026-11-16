select
    line_id,
    line_name,
    mode_name,
    created_source_at,
    modified_source_at,
    source_endpoint,
    ingested_at
from {{ source('raw_snapshot', 'tfl_lines') }}

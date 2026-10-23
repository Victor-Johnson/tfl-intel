with observed_lines as (
    select
        line_id,
        arg_max(line_name, observed_at) as line_name,
        arg_max(mode_name, observed_at) as mode_name,
        min(observed_at) as first_observed_at,
        max(observed_at) as last_observed_at
    from {{ ref('stg_line_status_observations') }}
    group by line_id
)
select
    coalesce(reference.line_id, observed.line_id) as line_id,
    coalesce(reference.line_name, observed.line_name) as line_name,
    coalesce(reference.mode_name, observed.mode_name) as mode_name,
    reference.created_source_at,
    reference.modified_source_at,
    observed.first_observed_at,
    observed.last_observed_at,
    reference.line_id is not null as has_reference_metadata
from observed_lines as observed
full outer join {{ ref('stg_lines') }} as reference using (line_id)


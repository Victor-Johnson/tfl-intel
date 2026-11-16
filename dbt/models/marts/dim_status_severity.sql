with observed_statuses as (
    select
        status_severity as severity_level,
        arg_max(status_description, observed_at) as description,
        arg_max(mode_name, observed_at) as mode_name,
        min(observed_at) as first_observed_at,
        max(observed_at) as last_observed_at
    from {{ ref('stg_line_status_observations') }}
    group by status_severity
),
reference_statuses as (
    select
        severity_level,
        arg_max(description, ingested_at) as description,
        arg_max(mode_name, ingested_at) as mode_name,
        max(ingested_at) as reference_ingested_at
    from {{ ref('stg_status_severity_codes') }}
    group by severity_level
)
select
    coalesce(reference.severity_level, observed.severity_level)
        as severity_level,
    coalesce(reference.description, observed.description) as description,
    coalesce(reference.mode_name, observed.mode_name) as mode_name,
    lower(coalesce(reference.description, observed.description))
        <> 'good service' as is_disrupted,
    case
        when lower(coalesce(reference.description, observed.description))
            = 'good service' then 0
        when lower(coalesce(reference.description, observed.description))
            like '%closed%' then 100
        when lower(coalesce(reference.description, observed.description))
            like '%closure%' then 100
        when lower(coalesce(reference.description, observed.description))
            like '%suspend%' then 90
        when lower(coalesce(reference.description, observed.description))
            like '%severe%' then 80
        when lower(coalesce(reference.description, observed.description))
            like '%minor%' then 70
        else 60
    end as disruption_priority,
    observed.first_observed_at,
    observed.last_observed_at,
    reference.reference_ingested_at,
    reference.severity_level is not null as has_reference_metadata
from observed_statuses as observed
full outer join reference_statuses as reference using (severity_level)


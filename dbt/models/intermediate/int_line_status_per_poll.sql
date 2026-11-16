{{ config(alias='line_status_per_poll') }}

with classified as (
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
        ingested_at,
        lower(trim(status_description)) as normalized_status_description,
        lower(trim(status_description)) <> 'good service' as is_disrupted,
        case
            when lower(trim(status_description)) = 'good service' then 0
            when lower(status_description) like '%closed%' then 100
            when lower(status_description) like '%closure%' then 100
            when lower(status_description) like '%suspend%' then 90
            when lower(status_description) like '%severe%' then 80
            when lower(status_description) like '%minor%' then 70
            else 60
        end as disruption_priority,
        count(*) over (
            partition by ingestion_run_id, line_id
        ) as source_status_count
    from {{ ref('stg_line_status_observations') }}
),
canonical_run_status as (
    select *
    from classified
    qualify row_number() over (
        partition by ingestion_run_id, line_id
        order by
            disruption_priority desc,
            observed_at desc,
            ingested_at desc,
            observation_id desc
    ) = 1
),
bucketed as (
    select
        *,
        time_bucket(interval '5 minutes', observed_at) as observation_bucket
    from canonical_run_status
)
select
    observation_id,
    ingestion_run_id,
    line_id,
    line_name,
    mode_name,
    status_severity,
    status_description,
    normalized_status_description,
    reason,
    is_disrupted,
    disruption_priority,
    source_status_count,
    observation_bucket,
    observed_at,
    ingested_at
from bucketed
qualify row_number() over (
    partition by line_id, observation_bucket
    order by
        observed_at desc,
        ingested_at desc,
        observation_id desc
) = 1


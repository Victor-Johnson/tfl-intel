{{ config(alias='line_status_intervals') }}

with sequenced as (
    select
        *,
        lead(observed_at) over (
            partition by line_id
            order by observed_at, observation_id
        ) as next_observed_at
    from {{ ref('int_line_status_per_poll') }}
),
measured as (
    select
        *,
        date_diff('second', observed_at, next_observed_at) / 60.0
            as elapsed_minutes
    from sequenced
)
select
    line_id,
    line_name,
    observation_id,
    ingestion_run_id,
    status_description,
    status_severity,
    reason,
    is_disrupted,
    disruption_priority,
    observed_at as interval_started_at,
    next_observed_at as interval_ended_at,
    elapsed_minutes,
    case
        when elapsed_minutes is null or elapsed_minutes <= 0 then 0.0
        else least(elapsed_minutes, 5.0)
    end as attributed_minutes,
    case
        when elapsed_minutes > 5.0 then elapsed_minutes - 5.0
        else 0.0
    end as unknown_gap_minutes,
    coalesce(elapsed_minutes > 10.0, false) as is_data_gap
from measured


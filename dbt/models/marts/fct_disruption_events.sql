{{ config(alias='disruption_events') }}

with ordered as (
    select
        *,
        lag(is_disrupted) over line_history as previous_is_disrupted,
        lag(observed_at) over line_history as previous_observed_at
    from {{ ref('int_line_status_per_poll') }}
    window line_history as (
        partition by line_id order by observed_at, observation_id
    )
),
boundaries as (
    select
        *,
        case
            when previous_is_disrupted is null then 1
            when is_disrupted <> previous_is_disrupted then 1
            when date_diff('minute', previous_observed_at, observed_at) > 10
                then 1
            else 0
        end as starts_new_segment
    from ordered
),
segmented as (
    select
        *,
        sum(starts_new_segment) over (
            partition by line_id
            order by observed_at, observation_id
            rows between unbounded preceding and current row
        ) as segment_number
    from boundaries
),
status_segments as (
    select
        line_id,
        max(line_name) as line_name,
        max(coalesce(mode_name, 'unknown')) as mode_name,
        segment_number,
        bool_or(is_disrupted) as is_disrupted,
        min(observed_at) as segment_started_at,
        max(observed_at) as segment_last_observed_at,
        count(*) as observation_count,
        max(disruption_priority) as worst_disruption_priority,
        arg_max(status_description, disruption_priority)
            as worst_status_description,
        arg_max(reason, observed_at) filter (where reason is not null)
            as latest_reason
    from segmented
    group by line_id, segment_number
),
with_next_segment as (
    select
        *,
        lead(segment_started_at) over segment_history
            as next_segment_started_at,
        lead(is_disrupted) over segment_history as next_segment_is_disrupted
    from status_segments
    window segment_history as (
        partition by line_id order by segment_number
    )
),
events as (
    select
        md5(line_id || '|' || cast(segment_started_at as varchar))
            as disruption_event_id,
        line_id,
        line_name,
        mode_name,
        segment_started_at as event_started_at,
        case
            when next_segment_is_disrupted = false
                and date_diff(
                    'minute',
                    segment_last_observed_at,
                    next_segment_started_at
                ) <= 10
                then next_segment_started_at
        end as event_ended_at,
        observation_count,
        observation_count * 5 as observed_disruption_minutes,
        worst_status_description,
        worst_disruption_priority,
        latest_reason
    from with_next_segment
    where is_disrupted
)
select
    disruption_event_id,
    line_id,
    line_name,
    mode_name,
    event_started_at,
    event_ended_at,
    case
        when event_ended_at is not null
            then date_diff('second', event_started_at, event_ended_at) / 60.0
    end as event_duration_minutes,
    observation_count,
    observed_disruption_minutes,
    worst_status_description,
    worst_disruption_priority,
    latest_reason,
    event_ended_at is not null as is_resolved
from events

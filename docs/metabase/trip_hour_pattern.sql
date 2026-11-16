with bounds as (
    select (now() at time zone 'Europe/London')::date as local_today
),
expected as (
    select
        extract(dow from slot at time zone 'Europe/London')::integer
            as weekday_index,
        extract(hour from slot at time zone 'Europe/London')::integer
            as hour_of_day,
        count(*) as expected_samples
    from bounds,
         generate_series(
             (local_today - 90)::timestamp at time zone 'Europe/London',
             local_today::timestamp at time zone 'Europe/London'
                 - interval '5 minutes',
             interval '5 minutes'
         ) as slots(slot)
    group by 1, 2
),
observed as (
    select
        weekday_index,
        hour_of_day,
        sum(observation_count) as observed_samples,
        sum(disrupted_observation_count) as disrupted_samples
    from analytics.line_disruption_hourly, bounds
    where service_date >= local_today - 90
      and service_date < local_today
      and line_id = {{line_id}}
    group by 1, 2
)
select
    expected.weekday_index,
    case expected.weekday_index
        when 0 then 'Sun'
        when 1 then 'Mon'
        when 2 then 'Tue'
        when 3 then 'Wed'
        when 4 then 'Thu'
        when 5 then 'Fri'
        else 'Sat'
    end as weekday_name,
    expected.hour_of_day,
    coalesce(observed.observed_samples, 0) as observed_samples,
    coalesce(observed.disrupted_samples, 0) as disrupted_samples,
    expected.expected_samples,
    round(100.0 * observed.disrupted_samples
        / nullif(observed.observed_samples, 0), 1)
        as observed_disruption_pct,
    round(100.0 * coalesce(observed.observed_samples, 0)
        / expected.expected_samples, 1) as coverage_pct,
    case
        when coalesce(observed.observed_samples, 0)
            < expected.expected_samples * 0.70 then 'insufficient'
        when observed.observed_samples
            < expected.expected_samples * 0.90 then 'provisional'
        else 'reliable'
    end as coverage_quality
from expected
left join observed using (weekday_index, hour_of_day)
order by expected.weekday_index, expected.hour_of_day;

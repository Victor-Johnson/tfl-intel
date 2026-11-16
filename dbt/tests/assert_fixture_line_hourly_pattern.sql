{% if env_var('TFL_DBT_CI_FIXTURE', 'false') == 'true' %}
with target as (
    select * from {{ ref('line_disruption_hourly') }}
    where line_id = 'timeline'
      and service_date = date '2026-07-14'
      and hour_of_day = 11
)
select 'incorrect line-hour sample totals' as failure
from target
where weekday_index <> 2
   or observation_count <> 4
   or disrupted_observation_count <> 2
   or observed_disruption_pct <> 50
union all
select 'missing line-hour sample totals'
where not exists (select 1 from target)
{% else %}
select 1 where false
{% endif %}

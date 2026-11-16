with latest_run as (
    select
        ingestion_run_id,
        status,
        started_at,
        finished_at,
        records_received,
        records_inserted
    from {{ ref('stg_pipeline_runs') }}
    qualify row_number() over (
        order by started_at desc, ingestion_run_id desc
    ) = 1
),
latest_success as (
    select max(finished_at) as latest_success_finished_at
    from {{ ref('stg_pipeline_runs') }}
    where status = 'success'
)
select
    latest_run.ingestion_run_id,
    latest_run.status,
    latest_run.started_at,
    latest_run.finished_at,
    latest_run.records_received,
    latest_run.records_inserted,
    latest_success.latest_success_finished_at
from latest_run
cross join latest_success

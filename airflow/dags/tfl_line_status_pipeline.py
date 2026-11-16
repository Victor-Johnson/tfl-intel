from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "victor",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    dag_id="tfl_line_status_pipeline",
    description=(
        "Ingest TfL status data, build and validate DuckDB marts, then check API."
    ),
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["tfl", "ingestion", "duckdb", "serving"],
) as dag:
    # bash operator using the bash command use trailing space commands for the sh files 
    ingest_line_status = BashOperator(
        task_id="ingest_line_status",
        bash_command="bash /workspace/scripts/run_ingest_line_status.sh ",
    )

    snapshot_postgres = BashOperator(
        task_id="snapshot_postgres_to_duckdb",
        bash_command="bash /workspace/scripts/snapshot_postgres_to_duckdb.sh ",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="bash /workspace/scripts/run_dbt_build.sh ",
    )

    validate_marts = BashOperator(
        task_id="validate_marts",
        bash_command=(
            "/opt/tfl-venv/bin/python "
            "/workspace/scripts/validate_duckdb_marts.py "
            "/data/tfl_intel_building.duckdb"
        ),
    )

    promote_snapshot = BashOperator(
        task_id="promote_duckdb_snapshot",
        bash_command=(
            "/opt/tfl-venv/bin/python "
            "/workspace/scripts/manage_duckdb_snapshot.py promote "
            "/data/tfl_intel.duckdb /data/tfl_intel_building.duckdb"
        ),
    )

    publish_bi_marts = BashOperator(
        task_id="publish_bi_marts",
        bash_command="bash /workspace/scripts/run_publish_bi_marts.sh ",
    )

    check_api_ready = BashOperator(
        task_id="check_api_ready",
        bash_command="bash /workspace/scripts/check_api_ready.sh ",
    )

    (
        ingest_line_status
        >> snapshot_postgres
        >> dbt_build
        >> validate_marts
        >> promote_snapshot
        >> check_api_ready
        >> publish_bi_marts
    )

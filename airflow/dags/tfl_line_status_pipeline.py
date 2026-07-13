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
    description="Ingest TfL line status data, refresh DuckDB analytics, and check the API.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["tfl", "ingestion", "duckdb", "serving"],
) as dag:
    ingest_line_status = BashOperator(
        task_id="ingest_line_status",
        bash_command="/workspace/scripts/run_ingest_line_status.sh",
    )

    refresh_duckdb = BashOperator(
        task_id="refresh_duckdb",
        bash_command="/workspace/scripts/refresh_duckdb_from_postgres.sh",
    )

    check_api_ready = BashOperator(
        task_id="check_api_ready",
        bash_command="/workspace/scripts/check_api_ready.sh",
    )

    ingest_line_status >> refresh_duckdb >> check_api_ready
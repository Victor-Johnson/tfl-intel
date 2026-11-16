from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "victor",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="tfl_reference_data_pipeline",
    description="Refresh TfL line and status-severity reference data.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["tfl", "reference-data", "postgres"],
) as dag:
    # A trailing space prevents BashOperator treating `.sh` as a Jinja file.
    ingest_reference_data = BashOperator(
        task_id="ingest_reference_data",
        bash_command="bash /workspace/scripts/run_ingest_reference_data.sh ",
    )

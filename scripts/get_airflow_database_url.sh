#!/usr/bin/env sh
set -eu

password_file="${AIRFLOW_DB_PASSWORD_FILE:-/run/secrets/airflow_db_password}"

if [ ! -r "$password_file" ]; then
  echo "Airflow database password is not readable at $password_file" >&2
  exit 1
fi

printf 'postgresql+psycopg2://airflow:%s@airflow-db:5432/airflow' \
  "$(cat "$password_file")"

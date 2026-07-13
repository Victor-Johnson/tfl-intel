#!/usr/bin/env sh
set -eu

if [! -f/run/secrets/postgres_password]; then 
    echo "Missing Docker secrets : /run/secrets/postgres_password"
    exit 1 
fi

POSTGRES_PASSWORD_VALUE = "$(cat /run/secrets/postgres_password)"

export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD_VALUE}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

cd /workspace

uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

## Purpose : Runs Airflow task -> wrapper script -> reads docker secrets -> builds DATABASE_URL -> runs ingestion
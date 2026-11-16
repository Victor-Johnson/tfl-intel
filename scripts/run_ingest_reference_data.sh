#!/usr/bin/env sh
set -eu

POSTGRES_PASSWORD_FILE="${POSTGRES_PASSWORD_FILE:-/run/secrets/postgres_password}"

if [ ! -r "$POSTGRES_PASSWORD_FILE" ]; then
  echo "Postgres password secret is not readable at $POSTGRES_PASSWORD_FILE" >&2
  exit 1
fi

POSTGRES_PASSWORD_VALUE="$(cat "$POSTGRES_PASSWORD_FILE")"
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD_VALUE}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

cd /workspace

if [ -n "${TFL_PYTHON:-}" ]; then
  "$TFL_PYTHON" -m tfl_intel.ingestion.jobs.ingest_severity_codes
  exec "$TFL_PYTHON" -m tfl_intel.ingestion.jobs.ingest_lines_by_mode
fi

uv run python -m tfl_intel.ingestion.jobs.ingest_severity_codes
exec uv run python -m tfl_intel.ingestion.jobs.ingest_lines_by_mode

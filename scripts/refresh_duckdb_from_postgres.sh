#!/usr/bin/env sh
set -eu

POSTGRES_PASSWORD_FILE="${POSTGRES_PASSWORD_FILE:-/run/secrets/postgres_password}"
DUCKDB_PATH="${DUCKDB_PATH:-/data/tfl_intel.duckdb}"

if [ ! -r "$POSTGRES_PASSWORD_FILE" ]; then
  echo "Postgres password secret is not readable at $POSTGRES_PASSWORD_FILE" >&2
  exit 1
fi

export PGPASSWORD
PGPASSWORD="$(cat "$POSTGRES_PASSWORD_FILE")"

uv run --no-project --with duckdb python /workspace/scripts/run_duckdb_sql.py \
  "$DUCKDB_PATH" \
  /workspace/sql/duckdb/refresh_from_postgres.sql

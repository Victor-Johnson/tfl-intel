#!/usr/bin/env sh
set -eu

POSTGRES_PASSWORD_FILE="${POSTGRES_PASSWORD_FILE:-/run/secrets/postgres_password}"
DUCKDB_PATH="${DUCKDB_PATH:-/data/tfl_intel.duckdb}"
DUCKDB_BUILD_PATH="${DUCKDB_BUILD_PATH:-${DUCKDB_PATH%.duckdb}_building.duckdb}"

if [ ! -r "$POSTGRES_PASSWORD_FILE" ]; then
  echo "Postgres password secret is not readable at $POSTGRES_PASSWORD_FILE" >&2
  exit 1
fi

export PGPASSWORD
PGPASSWORD="$(cat "$POSTGRES_PASSWORD_FILE")"
export PGHOST="${PGHOST:-${POSTGRES_HOST:-postgres}}"
export PGPORT="${PGPORT:-${POSTGRES_PORT:-5432}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-tfl_intel}}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-tfl_intel}}"

if [ -n "${TFL_PYTHON:-}" ]; then
  "$TFL_PYTHON" /workspace/scripts/manage_duckdb_snapshot.py \
    prepare "$DUCKDB_PATH" "$DUCKDB_BUILD_PATH"
  exec "$TFL_PYTHON" /workspace/scripts/run_duckdb_sql.py \
    "$DUCKDB_BUILD_PATH" /workspace/sql/duckdb/refresh_from_postgres.sql
fi

uv run --frozen --no-dev python \
  /workspace/scripts/manage_duckdb_snapshot.py \
  prepare "$DUCKDB_PATH" "$DUCKDB_BUILD_PATH"
exec uv run --frozen --no-dev python \
  /workspace/scripts/run_duckdb_sql.py \
  "$DUCKDB_BUILD_PATH" /workspace/sql/duckdb/refresh_from_postgres.sql

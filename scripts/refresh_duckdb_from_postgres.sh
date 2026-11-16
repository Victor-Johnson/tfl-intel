#!/usr/bin/env sh
set -eu

/workspace/scripts/snapshot_postgres_to_duckdb.sh
/workspace/scripts/run_dbt_build.sh

DUCKDB_PATH="${DUCKDB_PATH:-/data/tfl_intel.duckdb}"
DUCKDB_BUILD_PATH="${DUCKDB_BUILD_PATH:-${DUCKDB_PATH%.duckdb}_building.duckdb}"
if [ -n "${TFL_PYTHON:-}" ]; then
  "$TFL_PYTHON" /workspace/scripts/validate_duckdb_marts.py "$DUCKDB_BUILD_PATH"
  exec "$TFL_PYTHON" /workspace/scripts/manage_duckdb_snapshot.py \
    promote "$DUCKDB_PATH" "$DUCKDB_BUILD_PATH"
fi

uv run --frozen --no-dev python \
  /workspace/scripts/validate_duckdb_marts.py "$DUCKDB_BUILD_PATH"
exec uv run --frozen --no-dev python \
  /workspace/scripts/manage_duckdb_snapshot.py \
  promote "$DUCKDB_PATH" "$DUCKDB_BUILD_PATH"

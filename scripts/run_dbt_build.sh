#!/usr/bin/env sh
set -eu

DUCKDB_PATH="${DUCKDB_PATH:-/data/tfl_intel.duckdb}"
export DUCKDB_PATH="${DUCKDB_BUILD_PATH:-${DUCKDB_PATH%.duckdb}_building.duckdb}"
DBT_PROJECT_DIR="${DBT_PROJECT_DIR:-/workspace/dbt}"

if [ -n "${TFL_PYTHON:-}" ]; then
  exec /opt/tfl-venv/bin/dbt build \
    --project-dir "$DBT_PROJECT_DIR" \
    --profiles-dir "$DBT_PROJECT_DIR" \
    --log-path /tmp/dbt-logs \
    --target-path /tmp/dbt-target
fi

exec uv run --frozen --no-dev --group analytics dbt build \
  --project-dir "$DBT_PROJECT_DIR" \
  --profiles-dir "$DBT_PROJECT_DIR" \
  --log-path /tmp/dbt-logs \
  --target-path /tmp/dbt-target

#!/usr/bin/env sh
set -eu

if [ "${PUBLISH_BI_MARTS:-true}" != "true" ]; then
  echo "BI mart publication is disabled."
  exit 0
fi

export DUCKDB_PATH="${DUCKDB_PATH:-/data/tfl_intel.duckdb}"
exec "${TFL_PYTHON:-/opt/tfl-venv/bin/python}" \
  -m tfl_intel.analytics.publish_bi_marts

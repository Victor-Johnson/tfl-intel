#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_FILES=(
  -f docker-compose.yml
  -f docker-compose.airflow.yml
  -f docker-compose.metabase.yml
  -f docker-compose.production.yml
)

cd "$PROJECT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

for secret_file in \
  secrets/postgres_password.txt \
  secrets/airflow_db_password.txt \
  secrets/metabase_app_db_password.txt \
  secrets/metabase_reader_password.txt; do
  if [[ ! -s "$secret_file" ]]; then
    echo "Required secret is missing or empty: $secret_file" >&2
    exit 1
  fi
done

if [[ "${AIRFLOW_UID:-50000}" != "$(id -u)" ]]; then
  echo "Set AIRFLOW_UID in .env to the deployment account UID ($(id -u))." >&2
  echo "Airflow must be able to read owner-only secret files." >&2
  exit 1
fi

if [[ "$(<secrets/postgres_password.txt)" == "change_me" ]] || \
  [[ "$(<secrets/airflow_db_password.txt)" == "change-me-airflow" ]] || \
  [[ "$(<secrets/metabase_app_db_password.txt)" == "change-me-metabase-app-db" ]] || \
  [[ "$(<secrets/metabase_reader_password.txt)" == "change-me-metabase-reader" ]]; then
  echo "Replace the example database passwords before production deployment." >&2
  exit 1
fi
if [[ "${AIRFLOW_ADMIN_PASSWORD:-airflow}" == "airflow" ]]; then
  echo "Replace the default Airflow administrator password in .env." >&2
  exit 1
fi
if [[ -z "${TFL_APP_KEY:-}" ]]; then
  echo "Set a registered TFL_APP_KEY in .env for production polling." >&2
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "Docker Buildx is required for Compose image builds." >&2
  echo "Install the docker-buildx-plugin package on the VPS." >&2
  exit 1
fi

proxy_network="${PROXY_NETWORK:-npm_proxy}"
if ! docker network inspect "$proxy_network" >/dev/null 2>&1; then
  echo "Docker network '$proxy_network' does not exist." >&2
  echo "Create it and attach Nginx Proxy Manager before deploying." >&2
  exit 1
fi

compose() {
  docker compose "${COMPOSE_FILES[@]}" "$@"
}

compose config --quiet
compose up -d --build

for attempt in {1..60}; do
  if compose exec -T postgres pg_isready \
    -U "${POSTGRES_USER:-tfl_intel}" \
    -d "${POSTGRES_DB:-tfl_intel}" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" == 60 ]]; then
    echo "Postgres did not become ready." >&2
    exit 1
  fi
  sleep 2
done

for migration in sql/postgres/*.sql; do
  compose exec -T postgres psql \
    -U "${POSTGRES_USER:-tfl_intel}" \
    -d "${POSTGRES_DB:-tfl_intel}" \
    -v ON_ERROR_STOP=1 < "$migration"
done

compose exec -T airflow-scheduler \
  bash /workspace/scripts/run_ingest_reference_data.sh
compose exec -T airflow-scheduler \
  bash /workspace/scripts/run_ingest_line_status.sh
compose exec -T airflow-scheduler \
  bash /workspace/scripts/snapshot_postgres_to_duckdb.sh
compose exec -T airflow-scheduler \
  bash /workspace/scripts/run_dbt_build.sh
compose exec -T airflow-scheduler \
  /opt/tfl-venv/bin/python /workspace/scripts/validate_duckdb_marts.py \
  /data/tfl_intel_building.duckdb
compose exec -T airflow-scheduler \
  /opt/tfl-venv/bin/python /workspace/scripts/manage_duckdb_snapshot.py \
  promote /data/tfl_intel.duckdb /data/tfl_intel_building.duckdb
compose exec -T airflow-scheduler \
  bash /workspace/scripts/check_api_ready.sh
compose run --rm bi-publisher
compose exec -T airflow-scheduler \
  airflow dags unpause tfl_line_status_pipeline
compose exec -T airflow-scheduler \
  airflow dags unpause tfl_reference_data_pipeline
compose exec -T airflow-scheduler \
  bash /workspace/scripts/check_api_ready.sh

for attempt in {1..60}; do
  if curl --fail --silent \
    "http://127.0.0.1:${METABASE_PORT:-3000}/api/health" \
    >/dev/null; then
    break
  fi
  if [[ "$attempt" == 60 ]]; then
    echo "Metabase did not become ready." >&2
    exit 1
  fi
  sleep 2
done

echo "TfL Intel production bootstrap completed successfully."

#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/tfl-intel}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/tfl-intel}"
COMPOSE_FILES=(
  -f docker-compose.yml
  -f docker-compose.airflow.yml
  -f docker-compose.metabase.yml
  -f docker-compose.production.yml
)

if [[ "$BACKUP_DIR" != /var/backups/tfl-intel* ]]; then
  echo "BACKUP_DIR must be within /var/backups/tfl-intel." >&2
  exit 1
fi

mkdir -p \
  "$BACKUP_DIR/daily" \
  "$BACKUP_DIR/weekly" \
  "$BACKUP_DIR/metabase/daily" \
  "$BACKUP_DIR/metabase/weekly"
cd "$PROJECT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
daily_file="$BACKUP_DIR/daily/tfl_intel_${timestamp}.dump"
temporary_file="${daily_file}.partial"
metabase_daily_file="$BACKUP_DIR/metabase/daily/metabase_${timestamp}.dump"
metabase_temporary_file="${metabase_daily_file}.partial"

docker compose "${COMPOSE_FILES[@]}" exec -T postgres pg_dump \
  --username "${POSTGRES_USER:-tfl_intel}" \
  --dbname "${POSTGRES_DB:-tfl_intel}" \
  --format custom \
  --no-owner > "$temporary_file"
test -s "$temporary_file"
docker compose "${COMPOSE_FILES[@]}" exec -T postgres pg_restore \
  --list < "$temporary_file" >/dev/null
mv "$temporary_file" "$daily_file"

docker compose "${COMPOSE_FILES[@]}" exec -T metabase-db pg_dump \
  --username metabase \
  --dbname metabase \
  --format custom \
  --no-owner > "$metabase_temporary_file"
test -s "$metabase_temporary_file"
docker compose "${COMPOSE_FILES[@]}" exec -T metabase-db pg_restore \
  --list < "$metabase_temporary_file" >/dev/null
mv "$metabase_temporary_file" "$metabase_daily_file"

restore_check_db="tfl_restore_check_${timestamp}_$$"
cleanup_restore_check() {
  docker compose "${COMPOSE_FILES[@]}" exec -T postgres dropdb \
    --if-exists --username "${POSTGRES_USER:-tfl_intel}" \
    "$restore_check_db" >/dev/null || true
}
trap cleanup_restore_check EXIT

docker compose "${COMPOSE_FILES[@]}" exec -T postgres createdb \
  --template template0 --username "${POSTGRES_USER:-tfl_intel}" \
  "$restore_check_db"
docker compose "${COMPOSE_FILES[@]}" exec -T postgres pg_restore \
  --exit-on-error --single-transaction --no-owner --no-acl \
  --username "${POSTGRES_USER:-tfl_intel}" \
  --dbname "$restore_check_db" < "$daily_file"
restored_rows="$(docker compose "${COMPOSE_FILES[@]}" exec -T postgres psql \
  --username "${POSTGRES_USER:-tfl_intel}" --dbname "$restore_check_db" \
  --no-psqlrc --tuples-only --no-align --set ON_ERROR_STOP=1 \
  --command 'SELECT count(*) FROM raw.tfl_line_status_observations')"
echo "Verified operational backup restore: $restored_rows raw observations"
cleanup_restore_check
trap - EXIT

docker compose "${COMPOSE_FILES[@]}" exec -T postgres psql \
  --username "${POSTGRES_USER:-tfl_intel}" \
  --dbname "${POSTGRES_DB:-tfl_intel}" \
  --no-psqlrc --set ON_ERROR_STOP=1 --single-transaction \
  < sql/maintenance/prune_raw_90d.sql

if [[ "$(date -u +%u)" == 7 ]]; then
  cp "$daily_file" "$BACKUP_DIR/weekly/"
  cp "$metabase_daily_file" "$BACKUP_DIR/metabase/weekly/"
fi

mapfile -t old_daily < <(find "$BACKUP_DIR/daily" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +8 | cut -d' ' -f2-)
mapfile -t old_weekly < <(find "$BACKUP_DIR/weekly" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +5 | cut -d' ' -f2-)
mapfile -t old_metabase_daily < <(find "$BACKUP_DIR/metabase/daily" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +8 | cut -d' ' -f2-)
mapfile -t old_metabase_weekly < <(find "$BACKUP_DIR/metabase/weekly" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' | sort -rn | tail -n +5 | cut -d' ' -f2-)

if ((${#old_daily[@]})); then
  rm -- "${old_daily[@]}"
fi
if ((${#old_weekly[@]})); then
  rm -- "${old_weekly[@]}"
fi
if ((${#old_metabase_daily[@]})); then
  rm -- "${old_metabase_daily[@]}"
fi
if ((${#old_metabase_weekly[@]})); then
  rm -- "${old_metabase_weekly[@]}"
fi

echo "Created $daily_file and $metabase_daily_file; pruned raw history older than 90 days"

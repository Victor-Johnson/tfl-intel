#!/usr/bin/env sh
set -eu

# Fail the Airflow task on any unsuccessful response.
API_BASE_URL="${API_BASE_URL:-http://api:8000}"

curl --fail --silent --show-error "${API_BASE_URL}/health"
curl --fail --silent --show-error "${API_BASE_URL}/ready"
curl --fail --silent --show-error \
  "${API_BASE_URL}/api/v1/lines/current-status"

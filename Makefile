.PHONY: \
	postgres-up \
	postgres-init \
	ingest-line-status \
	ingest-reference-data \
	duckdb-refresh \
	dbt-parse \
	dbt-ci \
	dbt-docs \
	validate-marts \
	api-dev \
	api-docker \
	stack-up \
	stack-down \
	airflow-up \
	airflow-down \
	compose-config \
	production-config \
	production-bootstrap \
	metabase-up \
	metabase-down \
	provision-metabase \
	publish-bi \
	backup-postgres \
	smoke-api \
	test \
	lint \
	format \
	typecheck \
	check

postgres-up:
	docker compose up -d postgres

postgres-init:
	docker compose exec -T postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/01_create_schemas.sql
	docker compose exec -T postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/02_create_raw_tables.sql
	docker compose exec -T postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/03_create_indexes.sql
	docker compose exec -T postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/04_add_comments.sql

ingest-line-status:
	uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

ingest-reference-data:
	docker compose --profile tools run --rm --entrypoint /workspace/scripts/run_ingest_reference_data.sh duckdb

duckdb-refresh:
	docker compose run --rm --entrypoint /workspace/scripts/refresh_duckdb_from_postgres.sh duckdb

dbt-parse:
	DUCKDB_PATH=/tmp/tfl_intel_dbt_parse.duckdb uv run --group analytics dbt parse --project-dir dbt --profiles-dir dbt

dbt-ci:
	uv run python scripts/create_dbt_ci_fixture.py /tmp/tfl_intel_ci.duckdb
	TFL_DBT_CI_FIXTURE=true DUCKDB_PATH=/tmp/tfl_intel_ci.duckdb uv run --group analytics dbt build --project-dir dbt --profiles-dir dbt

dbt-docs:
	DUCKDB_PATH=/tmp/tfl_intel_ci.duckdb uv run --group analytics dbt docs generate --project-dir dbt --profiles-dir dbt

validate-marts:
	docker compose run --rm --entrypoint uv duckdb run --frozen --no-dev python /workspace/scripts/validate_duckdb_marts.py /data/tfl_intel.duckdb

api-dev:
	DUCKDB_PATH=data/tfl_intel.duckdb uv run uvicorn tfl_intel.serving.app:app --reload

api-docker:
	docker compose up api

stack-up:
	docker compose up -d --build postgres api

stack-down:
	docker compose down

airflow-up:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d --build

airflow-down:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml down

compose-config:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml config --quiet

production-config:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml -f docker-compose.metabase.yml -f docker-compose.production.yml config --quiet

metabase-up:
	docker compose -f docker-compose.yml -f docker-compose.metabase.yml up -d

metabase-down:
	docker compose -f docker-compose.yml -f docker-compose.metabase.yml stop metabase metabase-db

provision-metabase:
	uv run python -m tfl_intel.analytics.provision_metabase

publish-bi:
	docker compose -f docker-compose.yml -f docker-compose.metabase.yml run --rm bi-publisher

production-bootstrap:
	./scripts/bootstrap_production.sh

backup-postgres:
	./scripts/backup_postgres.sh

smoke-api:
	curl http://localhost:8000/health
	curl http://localhost:8000/ready
	curl http://localhost:8000/api/v1/lines/current-status
	curl http://localhost:8000/api/v1/lines/status-summary
	curl http://localhost:8000/api/v1/lines/reliability
	curl http://localhost:8000/api/v1/disruptions?limit=5
	curl http://localhost:8000/api/v1/network/reliability-by-mode?days=30
	curl http://localhost:8000/api/v1/network/status-mix?days=30
	curl http://localhost:8000/api/v1/network/disruption-heatmap?days=30
	curl http://localhost:8000/api/v1/pipeline/freshness

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check: lint test typecheck dbt-ci

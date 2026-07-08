.PHONY: \
	postgres-up \
	postgres-init \
	ingest-line-status \
	duckdb-refresh \
	api-dev \
	api-docker \
	smoke-api \
	test \
	lint \
	format \
	typecheck \
	check

postgres-up:
	docker compose up -d postgres

postgres-init:
	docker exec -i tfl_intel_postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/01_create_schemas.sql
	docker exec -i tfl_intel_postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/02_create_raw_tables.sql
	docker exec -i tfl_intel_postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/03_create_indexes.sql
	docker exec -i tfl_intel_postgres psql -U tfl_intel -d tfl_intel -v ON_ERROR_STOP=1 < sql/postgres/04_add_comments.sql

ingest-line-status:
	uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

duckdb-refresh:
	docker compose run --rm --entrypoint /workspace/scripts/refresh_duckdb_from_postgres.sh duckdb

api-dev:
	DUCKDB_PATH=data/tfl_intel.duckdb uv run uvicorn tfl_intel.serving.app:app --reload

api-docker:
	docker compose up api

smoke-api:
	curl http://localhost:8000/health
	curl http://localhost:8000/ready
	curl http://localhost:8000/api/v1/lines/current-status
	curl http://localhost:8000/api/v1/lines/status-summary
	curl http://localhost:8000/api/v1/pipeline/freshness

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check: lint test typecheck

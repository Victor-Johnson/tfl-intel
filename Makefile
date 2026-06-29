.PHONY: sync test lint format typecheck check run-ingest-line-status

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check: lint test typecheck

run-ingest-line-status:
	uv run python -m tfl_intel.ingestion.jobs.ingest_line_status

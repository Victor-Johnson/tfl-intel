"""Health and readiness routes."""

from fastapi import APIRouter

from tfl_intel.serving.config import load_settings
from tfl_intel.serving.db import check_required_tables, duckdb_path_exists
from tfl_intel.serving.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return process-level health."""

    return HealthResponse(status="ok", service="tfl-intel-serving")


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """Return readiness for DuckDB-backed analytical serving."""

    settings = load_settings()
    db_exists = duckdb_path_exists(settings.duckdb_path)
    tables_exist, missing_tables = check_required_tables()
    is_ready = db_exists and tables_exist

    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        duckdb_path=settings.duckdb_path,
        checks={
            "duckdb_file_exists": db_exists,
            "analytics_tables_exist": tables_exist,
        },
        missing_tables=missing_tables,
    )

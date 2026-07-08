"""FastAPI application for read-only TfL analytics serving."""

from fastapi import FastAPI

from tfl_intel.common.logging import configure_logging
from tfl_intel.serving.config import load_settings
from tfl_intel.serving.routers import health, line_status, pipeline

settings = load_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="TfL Transport Intelligence API",
    version="0.1.0",
    description="Read-only JSON API over DuckDB analytics snapshots.",
)

app.include_router(health.router)
app.include_router(line_status.router)
app.include_router(pipeline.router)

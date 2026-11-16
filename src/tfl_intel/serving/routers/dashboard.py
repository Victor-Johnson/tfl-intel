"""Serve the zero-build reliability dashboard."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(tags=["dashboard"])
DASHBOARD_PATH = Path(__file__).parent.parent / "static" / "dashboard.html"


@router.get("/", include_in_schema=False)
async def dashboard_root() -> RedirectResponse:
    """Send portfolio visitors directly to the dashboard."""

    return RedirectResponse(url="/dashboard", status_code=307)


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    """Return the bundled reliability dashboard."""

    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))

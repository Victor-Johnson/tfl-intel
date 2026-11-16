"""Serve the zero-build reliability dashboard."""

from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from tfl_intel.serving.config import get_settings

router = APIRouter(tags=["dashboard"])
DASHBOARD_PATH = Path(__file__).parent.parent / "static" / "dashboard.html"
BI_LINK_PLACEHOLDER = "<!-- BI_WORKSPACE_LINK -->"


def _bi_workspace_link() -> str:
    settings = get_settings()
    url = settings.bi_dashboard_url.strip()
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        if parsed.port is not None and not 0 < parsed.port < 65536:
            return ""
    except ValueError:
        return ""
    if not parsed.hostname or parsed.username or parsed.password:
        return ""
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        return ""
    if parsed.scheme not in {"http", "https"}:
        return ""
    label = (
        "Open BI demo (fixture data)"
        if settings.bi_dashboard_demo
        else "Open BI workspace"
    )
    return (
        '<p><a class="bi-link" href="'
        f'{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        f"{label} ↗</a></p>"
    )


@router.get("/", include_in_schema=False)
async def dashboard_root() -> RedirectResponse:
    """Send portfolio visitors directly to the dashboard."""

    return RedirectResponse(url="/dashboard", status_code=307)


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    """Return the bundled reliability dashboard."""

    html = DASHBOARD_PATH.read_text(encoding="utf-8")
    return HTMLResponse(html.replace(BI_LINK_PLACEHOLDER, _bi_workspace_link()))

"""Create the curated trip-planning dashboard through Metabase's REST API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

SQL_DIR = Path(__file__).resolve().parents[3] / "docs" / "metabase"
DATABASE_NAME = "TfL Intel Analytics"
COLLECTION_NAME = "Trip planning insights"
DASHBOARD_NAME = "Plan with observed line history"


@dataclass(frozen=True)
class Question:
    name: str
    filename: str
    display: str
    row: int
    col: int
    size_x: int
    size_y: int
    line_filter: bool = False


QUESTIONS = (
    Question("Collection freshness", "collection_health.sql", "table", 0, 0, 12, 5),
    Question("Find a line ID", "trip_line_choices.sql", "table", 0, 12, 12, 5),
    Question(
        "Selected line now", "trip_current_status.sql", "table", 5, 0, 24, 5, True
    ),
    Question(
        "Your line by weekday and hour",
        "trip_hour_pattern.sql",
        "table",
        10,
        0,
        24,
        9,
        True,
    ),
    Question(
        "Ninety complete days: service and coverage",
        "trip_daily_history.sql",
        "line",
        19,
        0,
        24,
        8,
        True,
    ),
    Question(
        "Comparable lines with 90%+ coverage",
        "trip_reliable_lines.sql",
        "bar",
        27,
        0,
        12,
        8,
    ),
    Question(
        "Recent sampled episodes",
        "trip_recent_episodes.sql",
        "table",
        27,
        12,
        12,
        8,
        True,
    ),
)


def _items(payload: Any) -> list[dict[str, Any]]:
    """Handle list and paginated Metabase list responses."""

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise RuntimeError("Unexpected Metabase list response")


def _request(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"Metabase {method} {path} failed ({response.status_code})")
    return response.json()


def _template_tags() -> dict[str, dict[str, str]]:
    return {
        "line_id": {
            "id": str(uuid4()),
            "name": "line_id",
            "display-name": "Line ID",
            "type": "text",
            "default": "central",
        }
    }


def _question_payload(
    question: Question, database_id: int, collection_id: int
) -> dict[str, Any]:
    native: dict[str, Any] = {
        "query": (SQL_DIR / question.filename).read_text(encoding="utf-8")
    }
    if question.line_filter:
        native["template-tags"] = _template_tags()
    return {
        "name": question.name,
        "type": "question",
        "display": question.display,
        "description": (
            "Observed samples only; not a forecast or journey planner. "
            "Check collection coverage before comparing lines."
        ),
        "visualization_settings": {},
        "collection_id": collection_id,
        "dataset_query": {
            "database": database_id,
            "type": "native",
            "native": native,
        },
    }


def local_admin_session(base_url: str, email: str, password: str) -> str:
    """Set up or log in to a loopback-only development Metabase instance."""

    parsed_url = httpx.URL(base_url)
    if parsed_url.scheme != "http" or parsed_url.host not in {
        "127.0.0.1",
        "localhost",
    }:
        raise ValueError("Admin-password setup is restricted to local Metabase")
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30.0) as client:
        properties = _request(client, "GET", "/api/session/properties")
        if properties.get("has-user-setup"):
            result = _request(
                client,
                "POST",
                "/api/session",
                json={"username": email, "password": password},
            )
        else:
            token = properties.get("setup-token")
            if not token:
                raise RuntimeError("Metabase setup token is missing")
            result = _request(
                client,
                "POST",
                "/api/setup",
                json={
                    "token": token,
                    "user": {
                        "first_name": "TfL",
                        "last_name": "Admin",
                        "email": email,
                        "password": password,
                    },
                    "prefs": {"site_name": "TfL Intel BI"},
                },
            )
    return str(result["id"])


def provision_dashboard(
    *,
    base_url: str,
    api_key: str,
    reader_password: str,
    session_id: str | None = None,
    postgres_host: str = "postgres",
    postgres_port: int = 5432,
    postgres_db: str = "tfl_intel",
) -> int:
    """Provision a private dashboard; never enable public sharing implicitly."""

    if (
        not (api_key or session_id)
        or not reader_password
        or reader_password.startswith("change-me")
    ):
        raise ValueError(
            "A Metabase API key and non-example reader password are required"
        )

    with httpx.Client(
        base_url=base_url.rstrip("/"),
        headers=(
            {"X-API-Key": api_key}
            if api_key
            else {"X-Metabase-Session": str(session_id)}
        ),
        timeout=30.0,
    ) as client:
        databases = _items(_request(client, "GET", "/api/database"))
        database = next(
            (item for item in databases if item.get("name") == DATABASE_NAME), None
        )
        if database is None:
            database = _request(
                client,
                "POST",
                "/api/database",
                json={
                    "name": DATABASE_NAME,
                    "engine": "postgres",
                    "details": {
                        "host": postgres_host,
                        "port": postgres_port,
                        "dbname": postgres_db,
                        "user": "metabase_reader",
                        "password": reader_password,
                    },
                },
            )
        database_id = database["id"]

        collections = _items(_request(client, "GET", "/api/collection"))
        collection = next(
            (item for item in collections if item.get("name") == COLLECTION_NAME),
            None,
        )
        if collection is None:
            collection = _request(
                client, "POST", "/api/collection", json={"name": COLLECTION_NAME}
            )
        collection_id = collection["id"]

        dashboards = _items(_request(client, "GET", "/api/dashboard"))
        existing = next(
            (
                item
                for item in dashboards
                if item.get("name") == DASHBOARD_NAME
                and item.get("collection_id") == collection_id
            ),
            None,
        )
        existing_dashcards: list[dict[str, Any]] = []
        if existing is not None:
            existing_dashboard = _request(
                client, "GET", f"/api/dashboard/{existing['id']}"
            )
            existing_dashcards = existing_dashboard["dashcards"]

        existing_cards: dict[str, dict[str, Any]] = {}
        for dashcard in existing_dashcards:
            if dashcard.get("card_id") is None:
                continue
            card = dashcard.get("card") or _request(
                client, "GET", f"/api/card/{dashcard['card_id']}"
            )
            existing_cards[card["name"]] = dashcard

        cards: list[dict[str, Any]] = []
        for index, question in enumerate(QUESTIONS, start=1):
            previous = existing_cards.get(question.name)
            method = "PUT" if previous else "POST"
            path = f"/api/card/{previous['card_id']}" if previous else "/api/card"
            card = _request(
                client,
                method,
                path,
                json=_question_payload(question, database_id, collection_id),
            )
            new_dashcard: dict[str, Any] = {
                "id": previous["id"] if previous else -index,
                "card_id": card["id"],
                "row": question.row,
                "col": question.col,
                "size_x": question.size_x,
                "size_y": question.size_y,
            }
            if question.line_filter:
                new_dashcard["parameter_mappings"] = [
                    {
                        "parameter_id": "line",
                        "card_id": card["id"],
                        "target": ["variable", ["template-tag", "line_id"]],
                    }
                ]
            cards.append(new_dashcard)

        managed_card_ids = {card["card_id"] for card in cards}
        for dashcard in existing_dashcards:
            if (
                dashcard.get("card_id") is None
                or dashcard["card_id"] not in managed_card_ids
            ):
                cards.append(
                    {
                        key: dashcard[key]
                        for key in (
                            "id",
                            "card_id",
                            "row",
                            "col",
                            "size_x",
                            "size_y",
                            "parameter_mappings",
                        )
                        if key in dashcard
                    }
                )

        parameters = [
            {
                "id": "line",
                "name": "Line ID (for example, central)",
                "slug": "line",
                "type": "string/=",
                "default": "central",
            }
        ]
        if existing is None:
            dashboard = _request(
                client,
                "POST",
                "/api/dashboard",
                json={
                    "name": DASHBOARD_NAME,
                    "description": (
                        "Historical observed line status for a possible trip. "
                        "The 90-day views exclude the incomplete current day. "
                        "They are not predictions, and sparse coverage is unknown data."
                    ),
                    "collection_id": collection_id,
                    "parameters": parameters,
                },
            )
            dashboard_id = int(dashboard["id"])
        else:
            dashboard_id = int(existing["id"])
        _request(
            client,
            "PUT",
            f"/api/dashboard/{dashboard_id}",
            json={"dashcards": cards, "parameters": parameters},
        )
        return dashboard_id


def main() -> None:
    """Provision from environment and an ignored local password file."""

    api_key = os.environ.get("METABASE_API_KEY", "")
    base_url = os.environ.get("METABASE_URL", "http://127.0.0.1:3000")
    session_id = None
    if not api_key:
        admin_file = Path(
            os.environ.get(
                "METABASE_ADMIN_PASSWORD_FILE",
                "secrets/metabase_local_admin_password.txt",
            )
        )
        if not admin_file.is_file():
            raise SystemExit("Set METABASE_API_KEY or a local admin password file")
        session_id = local_admin_session(
            base_url,
            os.environ.get("METABASE_ADMIN_EMAIL", "admin@localhost.invalid"),
            admin_file.read_text(encoding="utf-8").strip(),
        )
    password_file = Path(
        os.environ.get(
            "METABASE_READER_PASSWORD_FILE", "secrets/metabase_reader_password.txt"
        )
    )
    if not password_file.is_file():
        raise SystemExit(f"Missing reader password file: {password_file}")
    dashboard_id = provision_dashboard(
        base_url=base_url,
        api_key=api_key,
        reader_password=password_file.read_text(encoding="utf-8").strip(),
        session_id=session_id,
        postgres_host=os.environ.get("POSTGRES_HOST", "postgres"),
        postgres_port=int(os.environ.get("POSTGRES_PORT", "5432")),
        postgres_db=os.environ.get("POSTGRES_DB", "tfl_intel"),
    )
    print(f"Metabase trip dashboard: /dashboard/{dashboard_id}")


if __name__ == "__main__":
    main()

"""Verify the Metabase dashboard payload without external credentials."""

import json

import httpx
import pytest
import respx

from tfl_intel.analytics.provision_metabase import (
    QUESTIONS,
    local_admin_session,
    provision_dashboard,
)


def test_provision_dashboard_creates_restricted_trip_view() -> None:
    posted_cards: list[dict[str, object]] = []
    posted_database: list[dict[str, object]] = []
    posted_dashboard: list[dict[str, object]] = []
    updated_dashboard: list[dict[str, object]] = []

    def create_database(request: httpx.Request) -> httpx.Response:
        posted_database.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 4})

    def create_card(request: httpx.Request) -> httpx.Response:
        posted_cards.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 10 + len(posted_cards)})

    def create_dashboard(request: httpx.Request) -> httpx.Response:
        posted_dashboard.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 42})

    def update_dashboard(request: httpx.Request) -> httpx.Response:
        updated_dashboard.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 42})

    with respx.mock(base_url="http://metabase.test") as router:
        router.get("/api/database").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        router.post("/api/database").mock(side_effect=create_database)
        router.get("/api/collection").mock(return_value=httpx.Response(200, json=[]))
        router.post("/api/collection").mock(
            return_value=httpx.Response(200, json={"id": 7})
        )
        router.get("/api/dashboard").mock(return_value=httpx.Response(200, json=[]))
        router.post("/api/card").mock(side_effect=create_card)
        router.post("/api/dashboard").mock(side_effect=create_dashboard)
        router.put("/api/dashboard/42").mock(side_effect=update_dashboard)

        result = provision_dashboard(
            base_url="http://metabase.test",
            api_key="test-api-key",
            reader_password="test-reader-password",
        )

    assert result == 42
    assert posted_database[0]["details"]["user"] == "metabase_reader"
    assert posted_database[0]["details"]["host"] == "postgres"
    assert len(posted_cards) == len(QUESTIONS)
    assert posted_dashboard[0]["parameters"][0]["default"] == "central"
    assert len(updated_dashboard[0]["dashcards"]) == len(QUESTIONS)
    filtered = [
        card
        for card in updated_dashboard[0]["dashcards"]
        if card.get("parameter_mappings")
    ]
    assert len(filtered) == 4
    assert all(
        card["parameter_mappings"][0]["target"]
        == ["variable", ["template-tag", "line_id"]]
        for card in filtered
    )


def test_provision_dashboard_rejects_example_reader_password() -> None:
    with pytest.raises(ValueError, match="non-example reader password"):
        provision_dashboard(
            base_url="http://metabase.test",
            api_key="test-api-key",
            reader_password="change-me-metabase-reader",
        )


def test_provision_dashboard_updates_existing_questions() -> None:
    updated_cards: list[int] = []
    dashboard_updates: list[dict[str, object]] = []
    existing_cards = [
        {
            "id": 100 + index,
            "card_id": index,
            "card": {"id": index, "name": question.name},
            "row": question.row,
            "col": question.col,
            "size_x": question.size_x,
            "size_y": question.size_y,
        }
        for index, question in enumerate(QUESTIONS, start=1)
    ]

    def update_dashboard(request: httpx.Request) -> httpx.Response:
        dashboard_updates.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 42})

    with respx.mock(base_url="http://metabase.test") as router:
        router.get("/api/database").mock(
            return_value=httpx.Response(
                200, json={"data": [{"id": 4, "name": "TfL Intel Analytics"}]}
            )
        )
        router.get("/api/collection").mock(
            return_value=httpx.Response(
                200, json=[{"id": 7, "name": "Trip planning insights"}]
            )
        )
        router.get("/api/dashboard").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 42,
                        "name": "Plan with observed line history",
                        "collection_id": 7,
                    }
                ],
            )
        )
        router.get("/api/dashboard/42").mock(
            return_value=httpx.Response(200, json={"dashcards": existing_cards})
        )
        for index in range(1, len(QUESTIONS) + 1):
            router.put(f"/api/card/{index}").mock(
                return_value=httpx.Response(200, json={"id": index})
            )
        router.put("/api/dashboard/42").mock(side_effect=update_dashboard)

        result = provision_dashboard(
            base_url="http://metabase.test",
            api_key="test-api-key",
            reader_password="test-reader-password",
        )
        updated_cards = [
            index
            for index in range(1, len(QUESTIONS) + 1)
            if router.put(f"/api/card/{index}").called
        ]

    assert result == 42
    assert len(updated_cards) == len(QUESTIONS)
    assert len(dashboard_updates[0]["dashcards"]) == len(QUESTIONS)
    assert dashboard_updates[0]["dashcards"][0]["id"] == 101


def test_local_admin_session_sets_up_first_user() -> None:
    with respx.mock(base_url="http://127.0.0.1:3001") as router:
        router.get("/api/session/properties").mock(
            return_value=httpx.Response(
                200, json={"has-user-setup": False, "setup-token": "setup-token"}
            )
        )
        setup = router.post("/api/setup").mock(
            return_value=httpx.Response(200, json={"id": "session-id"})
        )
        session = local_admin_session(
            "http://127.0.0.1:3001", "admin@localhost.invalid", "test-password-123"
        )

    assert session == "session-id"
    assert json.loads(setup.calls[0].request.content)["token"] == "setup-token"


def test_local_admin_session_rejects_remote_password_login() -> None:
    with pytest.raises(ValueError, match="restricted to local"):
        local_admin_session("https://example.com", "a@b.test", "password")
    with pytest.raises(ValueError, match="restricted to local"):
        local_admin_session(
            "http://127.0.0.1.evil.example:3001", "a@b.test", "password"
        )

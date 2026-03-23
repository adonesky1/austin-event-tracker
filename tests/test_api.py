import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock


@pytest.fixture
def client():
    from src.main import app
    return TestClient(app)


@pytest.fixture
def admin_headers():
    from src.config.settings import Settings

    return {"x-api-key": Settings().admin_api_key}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_feedback_endpoint_rejects_invalid_token(client):
    response = client.get("/api/feedback/some-event-id?type=thumbs_up&token=invalid")
    assert response.status_code == 403


def test_feedback_endpoint_rejects_invalid_type(client):
    response = client.get("/api/feedback/some-event-id?type=invalid_type&token=anytoken")
    assert response.status_code == 400


def test_admin_requires_api_key(client):
    response = client.get("/admin/sources")
    assert response.status_code in (401, 403, 422)


def test_admin_sources_with_key(client, admin_headers):
    response = client.get("/admin/sources", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data


def test_admin_events_with_key(client, admin_headers):
    response = client.get("/admin/events", headers=admin_headers)
    assert response.status_code == 200


def test_digest_view_returns_html(client):
    import uuid
    digest_id = str(uuid.uuid4())
    response = client.get(f"/digests/{digest_id}")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_preferences_page(client):
    response = client.get("/preferences")
    assert response.status_code == 200


def test_feedback_valid_token_succeeds(client):
    from src.config.settings import Settings
    from src.digest.generator import DigestGenerator
    import uuid

    settings = Settings()
    generator = DigestGenerator(
        base_url="http://localhost:8000",
        feedback_secret=settings.feedback_secret,
    )
    event_id = str(uuid.uuid4())
    token = generator.serializer.dumps(event_id)

    response = client.get(f"/api/feedback/{event_id}?type=thumbs_up&token={token}")
    assert response.status_code == 200
    assert "Thanks" in response.text


def test_calendar_status_with_key(client, admin_headers, monkeypatch):
    async def fake_status():
        return {"enabled": False, "latest_run": None}

    monkeypatch.setattr("src.api.admin.get_latest_calendar_sync_status", fake_status)

    response = client.get("/admin/calendar/status", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_calendar_preview_with_key(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "src.api.admin.preview_google_calendar_sync",
        AsyncMock(
            return_value={
                "status": "success",
                "trigger": "manual_preview",
                "dry_run": True,
                "window_start": "2026-03-22",
                "window_end": "2026-04-12",
                "selected_count": 2,
                "created_count": 1,
                "updated_count": 1,
                "deleted_count": 0,
                "selected_events": [],
                "error": None,
            }
        ),
    )

    response = client.get("/admin/calendar/preview", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["dry_run"] is True


def test_calendar_sync_with_key(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "src.api.admin.run_google_calendar_sync",
        AsyncMock(
            return_value={
                "status": "success",
                "trigger": "manual",
                "dry_run": False,
                "window_start": "2026-03-22",
                "window_end": "2026-04-12",
                "selected_count": 2,
                "created_count": 1,
                "updated_count": 0,
                "deleted_count": 0,
                "selected_events": [],
                "error": None,
            }
        ),
    )

    response = client.post("/admin/calendar/sync", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_admin_profile_with_key(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "src.api.admin._with_session",
        AsyncMock(
            return_value={
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "admin@example.com",
                "city": "austin",
                "adults": [{"age": 35}],
                "children": [{"age": 8}],
                "preferred_neighborhoods": ["Zilker"],
                "max_distance_miles": 20,
                "preferred_days": ["saturday"],
                "preferred_times": ["afternoon"],
                "budget": "moderate",
                "interests": ["music"],
                "dislikes": [],
                "max_events_per_digest": 12,
                "crowd_sensitivity": "medium",
                "created_at": None,
                "updated_at": None,
            }
        ),
    )

    response = client.get("/admin/profile", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_admin_prompts_update_with_key(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "src.api.admin._with_session",
        AsyncMock(
            return_value={
                "key": "synthesis",
                "system_prompt": "custom system",
                "user_prompt_template": "custom user",
                "is_default": False,
                "updated_at": None,
            }
        ),
    )

    response = client.put(
        "/admin/prompts/synthesis",
        headers=admin_headers,
        json={"system_prompt": "custom system", "user_prompt_template": "custom user"},
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is False


def test_admin_tracked_items_create_with_key(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        "src.api.admin._with_session",
        AsyncMock(
            return_value={
                "id": "00000000-0000-0000-0000-000000000010",
                "label": "Spoon",
                "kind": "artist",
                "enabled": True,
                "boost_weight": 0.25,
                "notes": "Austin favorite",
                "created_at": None,
                "updated_at": None,
            }
        ),
    )

    response = client.post(
        "/admin/tracked-items",
        headers=admin_headers,
        json={
            "label": "Spoon",
            "kind": "artist",
            "enabled": True,
            "boost_weight": 0.25,
            "notes": "Austin favorite",
        },
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Spoon"

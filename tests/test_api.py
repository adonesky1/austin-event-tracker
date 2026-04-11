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


def test_jobs_with_key_include_persisted_recent_runs(client, admin_headers, monkeypatch):
    from datetime import datetime, timezone

    class FakeField:
        def __init__(self, name, value, is_default=False):
            self.name = name
            self.value = value
            self.is_default = is_default

        def __str__(self):
            return self.value

    class FakeTrigger:
        fields = [
            FakeField("day_of_week", "*", is_default=True),
            FakeField("hour", "6"),
        ]

    class FakeJob:
        id = "ingest_all_sources"
        name = "Ingest all sources"
        trigger = FakeTrigger()
        next_run_time = datetime(2026, 4, 11, 11, 0, tzinfo=timezone.utc)

    class FakeScheduler:
        def get_jobs(self):
            return [FakeJob()]

    monkeypatch.setattr("src.jobs.scheduler.get_scheduler", lambda: FakeScheduler())
    monkeypatch.setattr(
        "src.api.admin._with_session",
        AsyncMock(
            return_value={
                "ingest_all_sources": [
                    {
                        "id": "run-1",
                        "job_id": "ingest_all_sources",
                        "job_name": "Ingest all sources",
                        "trigger": "manual",
                        "status": "warning",
                        "started_at": "2026-04-10T12:00:00+00:00",
                        "completed_at": "2026-04-10T12:02:00+00:00",
                        "summary": "Ingested 12 events with 1 source error.",
                        "error": None,
                        "traceback": None,
                        "details": {"source_results": {"do512": {"status": "error"}}},
                        "created_at": "2026-04-10T12:02:00+00:00",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        "src.jobs.runtime_status.get_job_runtime_snapshot",
        lambda job_id, name: {
            "status": "idle",
            "trigger": None,
            "started_at": None,
            "completed_at": None,
            "summary": None,
            "error": None,
            "traceback": None,
            "details": None,
        },
    )

    response = client.get("/admin/jobs", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["runtime"]["status"] == "warning"
    assert payload[0]["recent_runs"][0]["summary"] == "Ingested 12 events with 1 source error."


def test_jobs_with_key_include_traceback_from_failed_recent_run(client, admin_headers, monkeypatch):
    from datetime import datetime, timezone

    class FakeField:
        def __init__(self, name, value, is_default=False):
            self.name = name
            self.value = value
            self.is_default = is_default

        def __str__(self):
            return self.value

    class FakeTrigger:
        fields = [
            FakeField("day_of_week", "sun"),
            FakeField("hour", "3"),
        ]

    class FakeJob:
        id = "cleanup_old_events"
        name = "Archive old events"
        trigger = FakeTrigger()
        next_run_time = datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc)

    class FakeScheduler:
        def get_jobs(self):
            return [FakeJob()]

    monkeypatch.setattr("src.jobs.scheduler.get_scheduler", lambda: FakeScheduler())
    monkeypatch.setattr(
        "src.api.admin._with_session",
        AsyncMock(
            return_value={
                "cleanup_old_events": [
                    {
                        "id": "run-2",
                        "job_id": "cleanup_old_events",
                        "job_name": "Archive old events",
                        "trigger": "scheduler",
                        "status": "failed",
                        "started_at": "2026-04-10T03:00:00+00:00",
                        "completed_at": "2026-04-10T03:00:05+00:00",
                        "summary": "Run failed.",
                        "error": "RuntimeError: Boom",
                        "traceback": "Traceback line 1\nTraceback line 2",
                        "details": None,
                        "created_at": "2026-04-10T03:00:05+00:00",
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        "src.jobs.runtime_status.get_job_runtime_snapshot",
        lambda job_id, name: {
            "status": "idle",
            "trigger": None,
            "started_at": None,
            "completed_at": None,
            "summary": None,
            "error": None,
            "traceback": None,
            "details": None,
        },
    )

    response = client.get("/admin/jobs", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["runtime"]["status"] == "failed"
    assert "Traceback line 1" in payload[0]["runtime"]["traceback"]
    assert "Traceback line 1" in payload[0]["recent_runs"][0]["traceback"]


def test_jobs_trigger_returns_conflict_when_already_running(client, admin_headers, monkeypatch):
    from datetime import datetime, timezone

    class FakeField:
        def __init__(self, name, value, is_default=False):
            self.name = name
            self.value = value
            self.is_default = is_default

        def __str__(self):
            return self.value

    class FakeTrigger:
        fields = [
            FakeField("day_of_week", "*", is_default=True),
            FakeField("hour", "6"),
        ]

    class FakeJob:
        id = "ingest_all_sources"
        name = "Ingest all sources"
        trigger = FakeTrigger()
        next_run_time = datetime(2026, 4, 11, 11, 0, tzinfo=timezone.utc)

    class FakeScheduler:
        def get_job(self, job_id):
            return FakeJob() if job_id == "ingest_all_sources" else None

    monkeypatch.setattr("src.jobs.scheduler.get_scheduler", lambda: FakeScheduler())
    monkeypatch.setattr(
        "src.jobs.scheduler.trigger_job_now",
        lambda job_id: (_ for _ in ()).throw(RuntimeError("Job 'Ingest all sources' is already running")),
    )

    response = client.post("/admin/jobs/ingest_all_sources/trigger", headers=admin_headers)
    assert response.status_code == 409
    assert "already running" in response.text


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

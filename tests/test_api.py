import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.main import app
    return TestClient(app)


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


def test_admin_sources_with_key(client):
    response = client.get("/admin/sources", headers={"x-api-key": "changeme"})
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data


def test_admin_events_with_key(client):
    response = client.get("/admin/events", headers={"x-api-key": "changeme"})
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
    from src.digest.generator import DigestGenerator
    import uuid

    generator = DigestGenerator(
        base_url="http://localhost:8000",
        feedback_secret="changeme",
    )
    event_id = str(uuid.uuid4())
    token = generator.serializer.dumps(event_id)

    response = client.get(f"/api/feedback/{event_id}?type=thumbs_up&token={token}")
    assert response.status_code == 200
    assert "Thanks" in response.text

from datetime import datetime, timedelta, timezone

import pytest

from src.integrations.calendar import (
    APP_MANAGED_PUBLISHER,
    GoogleCalendarIntegration,
    build_calendar_description,
    build_google_event_id,
    build_google_event_payload,
    build_google_maps_link,
    build_publication_key,
)
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema


def make_event(**overrides):
    base = {
        "title": "Kite Festival",
        "category": "kids",
        "start_datetime": datetime(2026, 3, 25, 16, 0, tzinfo=timezone.utc),
        "end_datetime": datetime(2026, 3, 25, 18, 0, tzinfo=timezone.utc),
        "city": "austin",
        "venue_name": "Zilker Park",
        "address": "2100 Barton Springs Rd",
        "canonical_event_url": "https://example.com/kite-festival",
        "editorial_summary": "A breezy afternoon of giant kites, open lawn play, and easy family hangs.",
        "relevance_explanation": "Great if your family wants an outdoor Austin plan with plenty of room for kids to roam.",
        "tags": ["kids", "outdoor"],
        "source_name": "eventbrite",
        "source_url": "https://example.com/source",
    }
    base.update(overrides)
    return NormalizedEvent(**base)


def make_settings(**overrides):
    from src.config.settings import Settings

    base = {
        "database_url": "sqlite+aiosqlite:///test.db",
        "anthropic_api_key": "test-key",
        "resend_api_key": "test-key",
        "google_calendar_enabled": True,
        "google_calendar_client_id": "client-id",
        "google_calendar_client_secret": "client-secret",
        "google_calendar_refresh_token": "refresh-token",
        "google_calendar_id": "calendar-id",
    }
    base.update(overrides)
    return Settings(**base)


def make_profile():
    return UserProfileSchema(
        email="test@example.com",
        children=[{"age": 5}],
        interests=["kids", "outdoor", "music"],
    )


def test_build_publication_key_prefers_canonical_url():
    event = make_event()
    assert build_publication_key(event) == "https://example.com/kite-festival"


def test_build_google_event_id_is_deterministic():
    key = "https://example.com/kite-festival"
    assert build_google_event_id(key) == build_google_event_id(key)
    assert build_google_event_id(key).startswith("aet")


def test_build_google_maps_link():
    event = make_event()
    link = build_google_maps_link(event)
    assert link is not None
    assert "google.com/maps/search" in link
    assert "Zilker+Park" in link


def test_build_calendar_description_includes_what_why_and_links():
    event = make_event()
    settings = make_settings()
    description = build_calendar_description(event, 0.91, make_profile(), settings=settings)
    assert "What:" in description
    assert "Why it fits:" in description
    assert "Links:" in description
    assert "https://example.com/kite-festival" in description
    assert "google.com/maps/search" in description


def test_build_calendar_description_falls_back_when_llm_text_missing():
    event = make_event(
        editorial_summary=None,
        relevance_explanation=None,
        canonical_event_url=None,
        source_url=None,
        category="community",
        tags=[],
    )
    description = build_calendar_description(event, 0.6, make_profile(), settings=make_settings())
    assert "What: Kite Festival at Zilker Park." in description
    assert "Why it fits:" in description
    assert "Links:" in description


def test_build_google_event_payload_contains_extended_properties():
    payload = build_google_event_payload(
        make_event(),
        0.88,
        make_profile(),
        make_settings(),
    )
    private = payload["extendedProperties"]["private"]
    assert private["publisher"] == APP_MANAGED_PUBLISHER
    assert private["publication_key"] == "https://example.com/kite-festival"
    assert "payload_hash" in private


def test_build_google_event_payload_uses_fallback_duration_when_end_missing():
    event = make_event(end_datetime=None)
    settings = make_settings(google_calendar_fallback_duration_minutes=90)
    payload = build_google_event_payload(event, 0.72, make_profile(), settings)
    start = datetime.fromisoformat(payload["start"]["dateTime"])
    end = datetime.fromisoformat(payload["end"]["dateTime"])
    assert payload["endTimeUnspecified"] is True
    assert end - start == timedelta(minutes=90)


class FakeRequest:
    def __init__(self, callback):
        self.callback = callback

    def execute(self):
        return self.callback()


class FakeEventsResource:
    def __init__(self, store):
        self.store = store

    def list(self, **kwargs):
        def callback():
            return {"items": list(self.store.values())}

        return FakeRequest(callback)

    def insert(self, *, calendarId, body):
        def callback():
            self.store[body["id"]] = body
            return body

        return FakeRequest(callback)

    def update(self, *, calendarId, eventId, body):
        def callback():
            self.store[eventId] = body
            return body

        return FakeRequest(callback)

    def delete(self, *, calendarId, eventId):
        def callback():
            self.store.pop(eventId, None)
            return {}

        return FakeRequest(callback)

    def get(self, *, calendarId, eventId):
        def callback():
            return self.store[eventId]

        return FakeRequest(callback)


class FakeCalendarsResource:
    def get(self, *, calendarId):
        return FakeRequest(lambda: {"id": calendarId})


class FakeGoogleService:
    def __init__(self, store):
        self.store = store
        self.events_resource = FakeEventsResource(store)
        self.calendars_resource = FakeCalendarsResource()

    def events(self):
        return self.events_resource

    def calendars(self):
        return self.calendars_resource


@pytest.mark.asyncio
async def test_sync_events_creates_updates_and_deletes(monkeypatch):
    store = {}
    settings = make_settings()
    integration = GoogleCalendarIntegration(settings)
    monkeypatch.setattr(integration, "_create_service", lambda: FakeGoogleService(store))

    profile = make_profile()
    event = make_event()
    first = await integration.sync_events([(event, 0.9)], profile, trigger="manual")
    assert first.created_count == 1
    assert len(store) == 1

    unchanged = await integration.preview_sync([(event, 0.9)], profile)
    assert unchanged.created_count == 0
    assert unchanged.updated_count == 0

    changed = make_event(editorial_summary="Updated summary for a family picnic vibe.")
    updated = await integration.sync_events([(changed, 0.9)], profile, trigger="manual")
    assert updated.updated_count == 1
    assert "Updated summary" in next(iter(store.values()))["description"]

    deleted = await integration.sync_events([], profile, trigger="manual")
    assert deleted.deleted_count == 1
    assert store == {}

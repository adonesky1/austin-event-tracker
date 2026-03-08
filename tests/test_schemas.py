from datetime import datetime, timezone


def test_raw_event_schema():
    from src.schemas.event import RawEvent

    raw = RawEvent(
        source_name="eventbrite",
        source_type="api",
        source_url="https://example.com/event/1",
        title="Test Event",
        start_datetime=datetime.now(timezone.utc),
        venue_name="Test Venue",
        city="austin",
    )
    assert raw.title == "Test Event"
    assert raw.source_name == "eventbrite"


def test_raw_event_defaults():
    from src.schemas.event import RawEvent

    raw = RawEvent(
        source_name="test",
        source_type="api",
        title="Minimal",
        start_datetime=datetime.now(timezone.utc),
        city="austin",
    )
    assert raw.currency == "USD"
    assert raw.tags == []
    assert raw.raw_payload is None


def test_normalized_event_schema():
    from src.schemas.event import NormalizedEvent

    event = NormalizedEvent(
        title="Test Event",
        category="music",
        start_datetime=datetime.now(timezone.utc),
        city="austin",
    )
    assert event.category == "music"
    assert event.id is not None
    assert event.confidence == 0.5


def test_user_profile_schema():
    from src.schemas.user import UserProfileSchema

    profile = UserProfileSchema(
        email="test@example.com",
        city="austin",
        interests=["music", "outdoor"],
    )
    assert profile.email == "test@example.com"
    assert profile.preferred_days == ["saturday", "sunday"]
    assert profile.budget == "moderate"


def test_source_health_schema():
    from src.schemas.source import SourceHealthSchema

    health = SourceHealthSchema(source_name="eventbrite", status="healthy", events_found=42)
    assert health.source_name == "eventbrite"
    assert health.events_found == 42

import pytest
from datetime import datetime, timezone

from src.schemas.event import NormalizedEvent
from src.dedupe.engine import DedupeEngine


def make_event(**kwargs):
    defaults = dict(
        title="Test Event",
        category="music",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        venue_name="Zilker Park",
        canonical_event_url=None,
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)


def test_exact_url_dedup():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(canonical_event_url="https://example.com/e/1", source_name="eventbrite"),
        make_event(canonical_event_url="https://example.com/e/1", source_name="do512"),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1


def test_exact_title_venue_date_dedup():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(
            title="SXSW 2026",
            venue_name="Convention Center",
            start_datetime=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            canonical_event_url="https://a.com/1",
        ),
        make_event(
            title="SXSW 2026",
            venue_name="Convention Center",
            start_datetime=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            canonical_event_url="https://b.com/2",
        ),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1


def test_different_events_not_deduped():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(title="Jazz Night", venue_name="Continental Club",
                   canonical_event_url="https://a.com/1"),
        make_event(title="Rock Show", venue_name="Mohawk",
                   canonical_event_url="https://b.com/2"),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 2


def test_fuzzy_near_identical_title_same_venue():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(
            title="Austin City Limits Music Festival",
            venue_name="Zilker Park",
            canonical_event_url="https://a.com/1",
        ),
        make_event(
            title="Austin City Limits Music Festival",
            venue_name="Zilker Park",
            canonical_event_url="https://b.com/2",
        ),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1


def test_dedup_keeps_richer_event():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(
            canonical_event_url="https://a.com/1",
            description=None,
            image_url=None,
        ),
        make_event(
            canonical_event_url="https://a.com/1",
            description="Great event with lots of detail",
            image_url="https://img.com/photo.jpg",
        ),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1
    assert deduped[0].description == "Great event with lots of detail"
    assert deduped[0].image_url == "https://img.com/photo.jpg"


def test_no_canonical_url_falls_through_to_tvd():
    engine = DedupeEngine(llm_client=None)
    events = [
        make_event(title="Folk Concert", venue_name="Emo's",
                   start_datetime=datetime(2026, 3, 15, 20, 0, tzinfo=timezone.utc)),
        make_event(title="Folk Concert", venue_name="Emo's",
                   start_datetime=datetime(2026, 3, 15, 20, 0, tzinfo=timezone.utc)),
    ]
    deduped = engine.deduplicate(events)
    assert len(deduped) == 1

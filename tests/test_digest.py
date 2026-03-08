import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from src.schemas.event import NormalizedEvent
from src.digest.sections import group_events_into_sections


def make_event(title, category="music", family_score=0.7, price_max=None,
               days_from_now=3, neighborhood=None, **kwargs):
    return NormalizedEvent(
        title=title,
        category=category,
        start_datetime=datetime.now(timezone.utc) + timedelta(days=days_from_now),
        city="austin",
        family_score=family_score,
        price_max=Decimal(str(price_max)) if price_max is not None else None,
        neighborhood=neighborhood,
        **kwargs,
    )


def test_group_events_creates_sections():
    events_with_scores = [
        (make_event("Top Event", family_score=0.95), 0.95),
        (make_event("Kids Fest", category="kids", family_score=0.9), 0.90),
        (make_event("Jazz Night", category="music", family_score=0.3), 0.80),
        (make_event("Free Concert", price_max=0, family_score=0.6), 0.70),
        (make_event("Future Fest", days_from_now=14, family_score=0.8), 0.75),
    ]
    sections = group_events_into_sections(events_with_scores)
    assert "top_picks" in sections
    assert len(sections["top_picks"]) <= 4


def test_kids_family_section_populated():
    events_with_scores = [
        (make_event("Kite Festival", category="kids", family_score=0.95), 0.95),
        (make_event("Comedy Night", category="theatre", family_score=0.2), 0.60),
    ]
    sections = group_events_into_sections(events_with_scores)
    assert "kids_family" in sections
    kids_titles = [e.title for e, _ in sections["kids_family"]]
    assert "Kite Festival" in kids_titles


def test_date_night_section_populated():
    events_with_scores = [
        (make_event("Adult Comedy", category="theatre", family_score=0.2), 0.80),
        (make_event("Kids Show", category="kids", family_score=0.9), 0.70),
    ]
    sections = group_events_into_sections(events_with_scores)
    assert "date_night" in sections
    date_titles = [e.title for e, _ in sections["date_night"]]
    assert "Adult Comedy" in date_titles


def test_free_cheap_section():
    events_with_scores = [
        (make_event("Free Park Concert", price_max=0), 0.80),
        (make_event("Expensive Gala", price_max=200), 0.90),
    ]
    sections = group_events_into_sections(events_with_scores)
    assert "free_cheap" in sections
    free_titles = [e.title for e, _ in sections["free_cheap"]]
    assert "Free Park Concert" in free_titles
    assert "Expensive Gala" not in free_titles


def test_digest_generator_renders_html():
    from src.digest.generator import DigestGenerator

    events_with_scores = [
        (make_event("Test Event", venue_name="Zilker Park",
                    editorial_summary="A great event for families.",
                    relevance_explanation="Perfect for your kids."), 0.9),
    ]
    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test")
    html = generator.render_html(
        events_with_scores, window_start="Mar 8", window_end="Mar 22"
    )
    assert "Test Event" in html
    assert "Zilker Park" in html
    assert "<html" in html.lower()
    assert "Austin Family Events" in html


def test_digest_generator_renders_plaintext():
    from src.digest.generator import DigestGenerator

    events_with_scores = [
        (make_event("Plaintext Event", venue_name="Stubb's"), 0.8),
    ]
    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test")
    text = generator.render_plaintext(
        events_with_scores, window_start="Mar 8", window_end="Mar 22"
    )
    assert "Plaintext Event" in text
    assert "AUSTIN FAMILY EVENTS" in text


def test_feedback_token_roundtrip():
    from src.digest.generator import DigestGenerator
    import uuid

    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test-secret")
    event_id = str(uuid.uuid4())
    token = generator.serializer.dumps(event_id)
    assert generator.verify_feedback_token(event_id, token) is True
    assert generator.verify_feedback_token(event_id, "bad-token") is False

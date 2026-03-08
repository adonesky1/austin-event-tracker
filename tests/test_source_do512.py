import pytest
from decimal import Decimal
from pathlib import Path

from src.sources.do512 import Do512Adapter


@pytest.fixture
def sample_html():
    return (Path(__file__).parent / "fixtures" / "do512_sample.html").read_text()


@pytest.fixture
def adapter():
    return Do512Adapter()


def test_do512_parses_html(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert len(events) == 3
    assert events[0].title == "SXSW Outdoor Stage at Lady Bird Lake"
    assert events[0].source_name == "do512"


def test_do512_extracts_venue(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[0].venue_name == "Auditorium Shores"
    assert events[1].venue_name == "Zilker Park"
    assert events[2].venue_name == "Comedy Mothership"


def test_do512_extracts_free_price(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[0].price_min == Decimal("0")


def test_do512_extracts_paid_price(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[2].price_min == Decimal("25")
    assert events[2].price_max == Decimal("45")


def test_do512_extracts_category(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "music" in events[0].tags
    assert "kids" in events[1].tags
    assert "theatre" in events[2].tags  # comedy -> theatre


def test_do512_extracts_url(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "do512.com" in events[0].canonical_event_url


def test_do512_extracts_description(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "Lady Bird Lake" in events[0].description

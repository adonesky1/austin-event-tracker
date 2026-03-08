import pytest
from decimal import Decimal
from pathlib import Path

from src.sources.austin_chronicle import AustinChronicleAdapter


@pytest.fixture
def sample_html():
    return (Path(__file__).parent / "fixtures" / "chronicle_sample.html").read_text()


@pytest.fixture
def adapter():
    return AustinChronicleAdapter()


def test_chronicle_parses_html(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert len(events) == 3
    assert events[0].title == "Blues on the Green"
    assert events[0].source_name == "austin_chronicle"
    assert events[0].source_type == "scraper"


def test_chronicle_extracts_venue(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[0].venue_name == "Zilker Park"
    assert events[2].venue_name == "Plaza Saltillo"


def test_chronicle_extracts_free_price(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[0].price_min == Decimal("0")
    assert events[0].price_max == Decimal("0")


def test_chronicle_extracts_category(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "music" in events[0].tags
    assert "arts" in events[1].tags
    assert "community" in events[2].tags


def test_chronicle_extracts_url(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "austinchronicle.com" in events[0].canonical_event_url


def test_chronicle_extracts_description(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert "outdoor concert" in events[0].description


def test_chronicle_extracts_image(adapter, sample_html):
    events = adapter.parse_listings(sample_html)
    assert events[0].image_url is not None
    assert events[1].image_url is None  # second event has no image

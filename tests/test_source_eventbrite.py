import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.sources.eventbrite import EventbriteAdapter

SAMPLE_RESPONSE = {
    "events": [
        {
            "id": "123",
            "name": {"text": "Austin Music Festival"},
            "description": {"text": "A great music festival in the heart of Austin"},
            "start": {"utc": "2026-03-15T15:00:00Z", "timezone": "America/Chicago"},
            "end": {"utc": "2026-03-15T22:00:00Z", "timezone": "America/Chicago"},
            "venue": {
                "name": "Zilker Park",
                "address": {
                    "localized_address_display": "2100 Barton Springs Rd, Austin, TX"
                },
                "latitude": "30.2669",
                "longitude": "-97.7725",
            },
            "url": "https://www.eventbrite.com/e/123",
            "logo": {"url": "https://img.example.com/logo.jpg"},
            "is_free": False,
            "ticket_availability": {
                "minimum_ticket_price": {"major_value": "25.00"},
                "maximum_ticket_price": {"major_value": "75.00"},
            },
            "category_id": "103",
            "subcategory_id": None,
        }
    ],
    "pagination": {"has_more_items": False},
}

SAMPLE_FREE_EVENT = {
    "events": [
        {
            "id": "456",
            "name": {"text": "Free Yoga in the Park"},
            "description": {"text": "Morning yoga session"},
            "start": {"utc": "2026-03-16T14:00:00Z"},
            "end": None,
            "venue": {
                "name": "Pease Park",
                "address": {"localized_address_display": "1100 Kingsbury St, Austin, TX"},
                "latitude": "30.2800",
                "longitude": "-97.7550",
            },
            "url": "https://www.eventbrite.com/e/456",
            "logo": None,
            "is_free": True,
            "ticket_availability": {},
            "category_id": "108",
        }
    ],
    "pagination": {"has_more_items": False},
}


@pytest.fixture
def adapter():
    return EventbriteAdapter(api_key="test-key")


@pytest.fixture
def austin_config():
    from src.config.city import load_city_config

    return load_city_config("austin")


@pytest.mark.asyncio
async def test_eventbrite_parses_events(adapter, austin_config):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    assert len(events) == 1
    e = events[0]
    assert e.title == "Austin Music Festival"
    assert e.venue_name == "Zilker Park"
    assert e.source_name == "eventbrite"
    assert e.price_min == Decimal("25.00")
    assert e.price_max == Decimal("75.00")
    assert e.canonical_event_url == "https://www.eventbrite.com/e/123"
    assert e.image_url == "https://img.example.com/logo.jpg"
    assert e.latitude == pytest.approx(30.2669)


@pytest.mark.asyncio
async def test_eventbrite_free_event(adapter, austin_config):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_FREE_EVENT
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    assert len(events) == 1
    assert events[0].price_min == Decimal("0")
    assert events[0].price_max == Decimal("0")


def test_eventbrite_disabled_without_key():
    adapter = EventbriteAdapter(api_key="")
    assert adapter.is_enabled() is False


def test_eventbrite_enabled_with_key():
    adapter = EventbriteAdapter(api_key="test-key")
    assert adapter.is_enabled() is True

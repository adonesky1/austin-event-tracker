import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.sources.bandsintown import BandsintownAdapter

SAMPLE_RESPONSE = [
    {
        "id": "456",
        "artist": {"name": "Khruangbin"},
        "venue": {
            "name": "ACL Live at The Moody Theater",
            "city": "Austin",
            "region": "TX",
            "country": "United States",
            "latitude": "30.2651",
            "longitude": "-97.7467",
            "location": "Austin, TX",
        },
        "datetime": "2026-03-20T20:00:00",
        "url": "https://www.bandsintown.com/e/456",
        "offers": [{"url": "https://tickets.example.com", "status": "available"}],
        "title": "Khruangbin at ACL Live",
        "description": "Live concert",
    },
    {
        "id": "789",
        "artist": {"name": "Black Pumas"},
        "venue": {
            "name": "Stubb's BBQ",
            "city": "Austin",
            "region": "TX",
            "latitude": "30.2685",
            "longitude": "-97.7355",
            "location": "Austin, TX",
        },
        "datetime": "2026-03-22T19:30:00",
        "url": "https://www.bandsintown.com/e/789",
        "offers": [],
        "title": "",
        "description": "",
    },
]


@pytest.fixture
def adapter():
    return BandsintownAdapter(app_id="test-app")


@pytest.fixture
def austin_config():
    from src.config.city import load_city_config

    return load_city_config("austin")


@pytest.mark.asyncio
async def test_bandsintown_parses_events(adapter, austin_config):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    assert len(events) == 2
    assert events[0].title == "Khruangbin at ACL Live"
    assert events[0].venue_name == "ACL Live at The Moody Theater"
    assert events[0].source_name == "bandsintown"
    assert events[0].city == "austin"
    assert "music" in events[0].tags


@pytest.mark.asyncio
async def test_bandsintown_builds_title_from_artist(adapter, austin_config):
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        events = await adapter.fetch_events(austin_config)

    # Second event has empty title, should be built from artist + venue
    assert events[1].title == "Black Pumas at Stubb's BBQ"


def test_bandsintown_disabled_without_app_id():
    adapter = BandsintownAdapter(app_id="")
    assert adapter.is_enabled() is False

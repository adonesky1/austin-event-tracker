import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema
from src.llm.synthesis import EventSynthesizer


def make_event(**kwargs):
    defaults = dict(
        title="Test Event",
        category="music",
        start_datetime=datetime.now(timezone.utc),
        city="austin",
        venue_name="Zilker Park",
        description="A fun outdoor music festival for all ages",
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)


@pytest.fixture
def profile():
    return UserProfileSchema(
        email="test@example.com",
        interests=["music", "outdoor"],
        children=[{"age": 5}, {"age": 8}],
        preferred_neighborhoods=["Zilker"],
    )


@pytest.mark.asyncio
async def test_synthesizer_enriches_events(profile):
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(return_value={
        "events": [
            {
                "index": 0,
                "family_score": 0.9,
                "editorial_summary": "A wonderful outdoor music festival perfect for families.",
                "relevance_explanation": "Great for your kids aged 5 and 8 in your favorite area.",
                "age_suitability": "all ages",
            }
        ]
    })

    synthesizer = EventSynthesizer(llm_client=mock_llm)
    events = [make_event()]
    enriched = await synthesizer.enrich_events(events, profile)

    assert enriched[0].family_score == 0.9
    assert "wonderful" in enriched[0].editorial_summary
    assert enriched[0].age_suitability == "all ages"
    assert enriched[0].relevance_explanation is not None


@pytest.mark.asyncio
async def test_synthesizer_handles_llm_failure(profile):
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(side_effect=Exception("LLM timeout"))

    synthesizer = EventSynthesizer(llm_client=mock_llm)
    events = [make_event()]
    enriched = await synthesizer.enrich_events(events, profile)

    # Should return original events unmodified on failure
    assert len(enriched) == 1
    assert enriched[0].family_score is None  # not set on failure


@pytest.mark.asyncio
async def test_synthesizer_clamps_family_score(profile):
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(return_value={
        "events": [{"index": 0, "family_score": 1.5, "editorial_summary": "Test",
                    "relevance_explanation": "Test", "age_suitability": "all ages"}]
    })

    synthesizer = EventSynthesizer(llm_client=mock_llm)
    events = [make_event()]
    enriched = await synthesizer.enrich_events(events, profile)

    assert enriched[0].family_score <= 1.0


@pytest.mark.asyncio
async def test_synthesizer_batches_large_inputs(profile):
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(return_value={"events": []})

    synthesizer = EventSynthesizer(llm_client=mock_llm)
    events = [make_event(title=f"Event {i}") for i in range(30)]
    await synthesizer.enrich_events(events, profile, batch_size=15)

    # Should have been called twice for 30 events with batch_size=15
    assert mock_llm.complete_json.call_count == 2

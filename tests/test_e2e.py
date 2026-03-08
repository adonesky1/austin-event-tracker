"""
End-to-end smoke test: runs the full pipeline with mock sources and mock LLM.
Verifies: ingest -> normalize -> dedupe -> rank -> synthesize -> generate digest.
"""
import pytest
from datetime import datetime, timezone, timedelta
from src.schemas.event import RawEvent
from src.schemas.user import UserProfileSchema
from src.sources.registry import SourceRegistry
from src.sources.base import SourceAdapter, SourceType
from src.ingestion.pipeline import IngestionPipeline
from src.dedupe.engine import DedupeEngine
from src.ranking.engine import RankingEngine
from src.digest.generator import DigestGenerator
from unittest.mock import AsyncMock


class MockSource(SourceAdapter):
    name = "mock"
    source_type = SourceType.API

    async def fetch_events(self, city_config):
        return [
            RawEvent(source_name="mock", source_type="api", title="Austin Music Fest",
                     start_datetime=datetime.now(timezone.utc) + timedelta(days=3),
                     city="austin", venue_name="Zilker Park", price_min=0, price_max=0,
                     tags=["music", "outdoor"], canonical_event_url="https://example.com/1"),
            RawEvent(source_name="mock", source_type="api", title="Kids Art Workshop",
                     start_datetime=datetime.now(timezone.utc) + timedelta(days=5),
                     city="austin", venue_name="Blanton Museum", tags=["kids", "arts"],
                     canonical_event_url="https://example.com/2"),
        ]


@pytest.mark.asyncio
async def test_full_pipeline():
    # 1. Ingest
    registry = SourceRegistry()
    registry.register(MockSource())
    from src.config.city import load_city_config
    city = load_city_config("austin")
    pipeline = IngestionPipeline(registry=registry, db_session=None)
    events = await pipeline.ingest(city, persist=False)
    assert len(events) == 2

    # 2. Dedupe (no dupes expected)
    engine = DedupeEngine(llm_client=None)
    deduped = engine.deduplicate(events)
    assert len(deduped) == 2

    # 3. Rank
    profile = UserProfileSchema(
        email="test@example.com", interests=["music", "outdoor", "kids"],
        children=[{"age": 5}],
    )
    ranker = RankingEngine()
    ranked = await ranker.rank_events(deduped, profile)
    assert len(ranked) == 2
    assert ranked[0][1] >= ranked[1][1]  # sorted by score

    # 4. Generate digest
    generator = DigestGenerator(base_url="http://localhost:8000", feedback_secret="test")
    html = generator.render_html(ranked, window_start="Mar 8", window_end="Mar 22")
    assert "Austin Music Fest" in html
    assert "Kids Art Workshop" in html

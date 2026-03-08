import pytest
from datetime import datetime, timezone

from src.schemas.event import RawEvent
from src.ingestion.normalizer import normalize_raw_event


def test_normalize_strips_whitespace():
    raw = RawEvent(
        source_name="eventbrite",
        source_type="api",
        title="  Test Event  ",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        venue_name="zilker park",
        city="Austin",
        tags=["music"],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.title == "Test Event"
    assert normalized.city == "austin"
    assert normalized.venue_name == "Zilker Park"


def test_normalize_preserves_source():
    raw = RawEvent(
        source_name="do512",
        source_type="scraper",
        title="Test",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        tags=["music"],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.source_name == "do512"
    assert normalized.source_type == "scraper"


def test_normalize_resolves_category():
    raw = RawEvent(
        source_name="test",
        source_type="api",
        title="Test",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        tags=["live music"],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.category == "music"


def test_normalize_defaults_category():
    raw = RawEvent(
        source_name="test",
        source_type="api",
        title="Test",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        tags=[],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.category == "community"


def test_normalize_bandsintown_defaults_music():
    raw = RawEvent(
        source_name="bandsintown",
        source_type="api",
        title="Concert",
        start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
        city="austin",
        tags=[],
    )
    normalized = normalize_raw_event(raw)
    assert normalized.category == "music"


@pytest.mark.asyncio
async def test_ingestion_pipeline_runs_enabled_sources():
    from src.sources.registry import SourceRegistry
    from src.sources.base import SourceAdapter
    from src.models.base import SourceType
    from src.ingestion.pipeline import IngestionPipeline
    from src.config.city import load_city_config

    class FakeSource(SourceAdapter):
        name = "fake"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            return [
                RawEvent(
                    source_name="fake",
                    source_type="api",
                    title="Fake Event",
                    start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
                    city="austin",
                    tags=["music"],
                )
            ]

        def rate_limit_delay(self):
            return 0

    registry = SourceRegistry()
    registry.register(FakeSource())

    city_config = load_city_config("austin")
    pipeline = IngestionPipeline(registry=registry, db_session=None)
    results = await pipeline.ingest(city_config, persist=False)
    assert len(results) == 1
    assert results[0].title == "Fake Event"


@pytest.mark.asyncio
async def test_ingestion_pipeline_handles_source_failure():
    from src.sources.registry import SourceRegistry
    from src.sources.base import SourceAdapter
    from src.models.base import SourceType
    from src.ingestion.pipeline import IngestionPipeline
    from src.config.city import load_city_config

    class FailingSource(SourceAdapter):
        name = "failing"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            raise RuntimeError("Source down")

        def rate_limit_delay(self):
            return 0

    class WorkingSource(SourceAdapter):
        name = "working"
        source_type = SourceType.API

        async def fetch_events(self, city_config):
            return [
                RawEvent(
                    source_name="working",
                    source_type="api",
                    title="Good Event",
                    start_datetime=datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc),
                    city="austin",
                    tags=["music"],
                )
            ]

        def rate_limit_delay(self):
            return 0

    registry = SourceRegistry()
    registry.register(FailingSource())
    registry.register(WorkingSource())

    city_config = load_city_config("austin")
    pipeline = IngestionPipeline(registry=registry, db_session=None)
    results = await pipeline.ingest(city_config, persist=False)
    assert len(results) == 1
    assert results[0].title == "Good Event"

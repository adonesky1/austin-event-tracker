import asyncio

import structlog

from src.config.city import CityConfig
from src.ingestion.normalizer import normalize_raw_event
from src.schemas.event import NormalizedEvent
from src.sources.registry import SourceRegistry

logger = structlog.get_logger()


class IngestionPipeline:
    def __init__(self, registry: SourceRegistry, db_session=None):
        self.registry = registry
        self.db_session = db_session
        self.last_results: dict[str, dict] = {}

    async def ingest(self, city_config: CityConfig, persist: bool = True) -> list[NormalizedEvent]:
        all_events: list[NormalizedEvent] = []
        results: dict[str, dict] = {}

        for source in self.registry.get_enabled():
            source_name = source.name
            try:
                logger.info("ingestion_source_start", source=source_name)
                raw_events = await source.fetch_events(city_config)
                normalized = [normalize_raw_event(e) for e in raw_events]
                all_events.extend(normalized)
                results[source_name] = {
                    "status": "success",
                    "count": len(normalized),
                }
                logger.info(
                    "ingestion_source_complete",
                    source=source_name,
                    count=len(normalized),
                )
            except Exception as e:
                results[source_name] = {
                    "status": "error",
                    "error": str(e),
                }
                logger.error(
                    "ingestion_source_failed",
                    source=source_name,
                    error=str(e),
                )

            await asyncio.sleep(source.rate_limit_delay())

        logger.info(
            "ingestion_complete",
            total_events=len(all_events),
            sources=results,
        )
        self.last_results = results

        if persist and self.db_session:
            await self._persist_events(all_events)

        return all_events

    async def _persist_events(self, events: list[NormalizedEvent]):
        from src.models.event import Event, EventSource
        from src.models.base import EventCategory, SourceType

        for event in events:
            db_event = Event(
                title=event.title,
                description=event.description,
                category=EventCategory(event.category),
                start_datetime=event.start_datetime,
                end_datetime=event.end_datetime,
                venue_name=event.venue_name,
                address=event.address,
                neighborhood=event.neighborhood,
                city=event.city,
                latitude=event.latitude,
                longitude=event.longitude,
                price_min=event.price_min,
                price_max=event.price_max,
                currency=event.currency,
                age_suitability=event.age_suitability,
                image_url=event.image_url,
                tags=event.tags,
                confidence=event.confidence,
                canonical_event_url=event.canonical_event_url,
            )
            self.db_session.add(db_event)

            source_record = EventSource(
                event_id=db_event.id,
                source_name=event.source_name or "",
                source_type=SourceType(event.source_type) if event.source_type else SourceType.API,
                source_url=event.source_url,
                title=event.title,
                start_datetime=event.start_datetime,
                venue_name=event.venue_name,
            )
            self.db_session.add(source_record)

        await self.db_session.commit()
        logger.info("ingestion_persisted", count=len(events))

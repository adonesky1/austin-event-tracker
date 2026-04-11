import structlog

from src.config.city import load_city_config
from src.config.settings import Settings
from src.ingestion.pipeline import IngestionPipeline
from src.models.database import create_engine, create_session_factory
from src.sources.austin_chronicle import AustinChronicleAdapter
from src.sources.bandsintown import BandsintownAdapter
from src.sources.do512 import Do512Adapter
from src.sources.eventbrite import EventbriteAdapter
from src.sources.instagram import InstagramAdapter
from src.sources.registry import SourceRegistry

logger = structlog.get_logger()


def build_registry(settings: Settings) -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(EventbriteAdapter(api_key=settings.eventbrite_api_key))
    registry.register(BandsintownAdapter(app_id=settings.bandsintown_app_id))
    registry.register(Do512Adapter())
    registry.register(AustinChronicleAdapter())
    registry.register(InstagramAdapter())
    return registry


async def run_ingestion():
    engine = None
    try:
        settings = Settings()
        city_config = load_city_config(settings.default_city)
        registry = build_registry(settings)
        engine = create_engine(settings)
        Session = create_session_factory(engine)
        async with Session() as session:
            pipeline = IngestionPipeline(registry=registry, db_session=session)
            events = await pipeline.ingest(city_config, persist=True)

        source_results = pipeline.last_results
        error_count = sum(1 for item in source_results.values() if item.get("status") == "error")
        success_count = sum(1 for item in source_results.values() if item.get("status") == "success")
        status = "warning" if error_count else "success"
        summary = (
            f"Ingested {len(events)} events from {success_count} sources."
            if not error_count
            else f"Ingested {len(events)} events with {error_count} source error(s)."
        )

        logger.info(
            "ingestion_job_complete",
            total=len(events),
            city=city_config.name,
            source_errors=error_count,
        )
        return {
            "status": status,
            "summary": summary,
            "city": city_config.name,
            "total_events": len(events),
            "source_results": source_results,
        }
    except Exception as exc:
        logger.error("ingestion_job_failed", error=str(exc))
        from src.notifications.error_notifier import notify_job_failure
        await notify_job_failure("ingest", exc)
        raise
    finally:
        if engine is not None:
            await engine.dispose()

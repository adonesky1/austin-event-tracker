import structlog

from src.config.city import load_city_config
from src.config.settings import Settings
from src.ingestion.pipeline import IngestionPipeline
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
    try:
        settings = Settings()
        city_config = load_city_config(settings.default_city)
        registry = build_registry(settings)

        pipeline = IngestionPipeline(registry=registry, db_session=None)
        events = await pipeline.ingest(city_config, persist=False)

        logger.info("ingestion_job_complete", total=len(events), city=city_config.name)
        return events
    except Exception as exc:
        logger.error("ingestion_job_failed", error=str(exc))
        from src.notifications.error_notifier import notify_job_failure
        await notify_job_failure("ingest", exc)
        raise

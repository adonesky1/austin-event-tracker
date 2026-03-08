from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter


class InstagramAdapter(SourceAdapter):
    """Stub adapter for Instagram events.

    Instagram's API is locked down to business account management only,
    and web scraping violates their ToS. Realistic future options:

    1. Use Apify or similar third-party scraping service
    2. Monitor specific venue/promoter accounts via Graph API
       (requires Facebook Business account)
    3. Manual curation feed from Instagram -> RSS bridge

    This adapter exists to hold the interface contract so it can be
    implemented when a viable approach is chosen.
    """

    name = "instagram"
    source_type = SourceType.SCRAPER

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        raise NotImplementedError("Instagram adapter not yet implemented")

    def is_enabled(self) -> bool:
        return False

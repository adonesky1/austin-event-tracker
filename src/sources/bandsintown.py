import asyncio
from datetime import datetime, timezone

import httpx
import structlog

from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter

logger = structlog.get_logger()


class BandsintownAdapter(SourceAdapter):
    name = "bandsintown"
    source_type = SourceType.API

    BASE_URL = "https://rest.bandsintown.com"

    def __init__(self, app_id: str):
        self.app_id = app_id

    def is_enabled(self) -> bool:
        return bool(self.app_id)

    def rate_limit_delay(self) -> float:
        return 0.5

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        events: list[RawEvent] = []

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/artists/all/events",
                    params={
                        "app_id": self.app_id,
                        "location": f"{city_config.latitude},{city_config.longitude}",
                        "radius": city_config.radius_miles,
                        "per_page": 100,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as e:
                logger.error("bandsintown_fetch_error", error=str(e))
                return events

            if not isinstance(data, list):
                logger.warning("bandsintown_unexpected_response", type=type(data).__name__)
                return events

            for raw in data:
                parsed = self._parse_event(raw, city_config)
                if parsed:
                    events.append(parsed)

        logger.info("bandsintown_fetch_complete", count=len(events))
        return events

    def _parse_event(self, raw: dict, city_config: CityConfig) -> RawEvent | None:
        try:
            venue = raw.get("venue") or {}
            artist = raw.get("artist") or {}
            artist_name = artist.get("name", "")

            title = raw.get("title") or ""
            if not title and artist_name:
                venue_name = venue.get("name", "")
                title = f"{artist_name} at {venue_name}" if venue_name else artist_name
            if not title:
                return None

            dt_str = raw.get("datetime")
            if not dt_str:
                return None
            start_dt = datetime.fromisoformat(dt_str)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            venue_city = venue.get("city", "")
            lat = _safe_float(venue.get("latitude"))
            lng = _safe_float(venue.get("longitude"))

            offers = raw.get("offers") or []
            ticket_url = offers[0].get("url") if offers else None

            return RawEvent(
                source_name=self.name,
                source_type=self.source_type.value,
                source_url=raw.get("url"),
                title=title,
                description=raw.get("description") or f"Live: {artist_name}",
                start_datetime=start_dt,
                venue_name=venue.get("name"),
                address=venue.get("location"),
                city=city_config.name,
                latitude=lat,
                longitude=lng,
                tags=["music", "live music"],
                canonical_event_url=raw.get("url") or ticket_url,
                raw_payload=raw,
            )
        except Exception as e:
            logger.warning("bandsintown_parse_error", error=str(e), event_id=raw.get("id"))
            return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

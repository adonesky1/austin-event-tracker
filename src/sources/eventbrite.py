import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import structlog

from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter

logger = structlog.get_logger()

# Eventbrite category IDs -> our categories
CATEGORY_MAP = {
    "103": "music",
    "105": "arts",
    "104": "festivals",
    "110": "community",  # food & drink -> community
    "113": "community",
    "115": "kids",  # family & education
    "108": "outdoor",  # sports & fitness
    "107": "seasonal",  # health
    "199": "theatre",  # performing arts
}


class EventbriteAdapter(SourceAdapter):
    name = "eventbrite"
    source_type = SourceType.API

    BASE_URL = "https://www.eventbriteapi.com/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def rate_limit_delay(self) -> float:
        return 0.5

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        events: list[RawEvent] = []
        page = 1
        has_more = True

        async with httpx.AsyncClient(timeout=30) as client:
            while has_more:
                try:
                    response = await client.get(
                        f"{self.BASE_URL}/events/search/",
                        params={
                            "location.latitude": city_config.latitude,
                            "location.longitude": city_config.longitude,
                            "location.within": f"{city_config.radius_miles}mi",
                            "expand": "venue,ticket_availability",
                            "page": page,
                        },
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPError as e:
                    logger.error("eventbrite_fetch_error", page=page, error=str(e))
                    break

                for raw in data.get("events", []):
                    parsed = self._parse_event(raw, city_config)
                    if parsed:
                        events.append(parsed)

                pagination = data.get("pagination", {})
                has_more = pagination.get("has_more_items", False)
                page += 1

                if has_more:
                    await asyncio.sleep(self.rate_limit_delay())

        logger.info("eventbrite_fetch_complete", count=len(events))
        return events

    def _parse_event(self, raw: dict, city_config: CityConfig) -> RawEvent | None:
        try:
            name = raw.get("name", {}).get("text", "").strip()
            if not name:
                return None

            start_str = raw.get("start", {}).get("utc")
            if not start_str:
                return None
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

            end_str = (raw.get("end") or {}).get("utc")
            end_dt = (
                datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else None
            )

            venue = raw.get("venue") or {}
            venue_name = venue.get("name")
            address = venue.get("address", {}).get("localized_address_display")
            lat = _safe_float(venue.get("latitude"))
            lng = _safe_float(venue.get("longitude"))

            price_min, price_max = self._extract_prices(raw)

            category_id = raw.get("category_id") or ""
            category = CATEGORY_MAP.get(category_id, "community")

            description = raw.get("description", {}).get("text", "")

            logo = raw.get("logo") or {}
            image_url = logo.get("url")

            return RawEvent(
                source_name=self.name,
                source_type=self.source_type.value,
                source_url=raw.get("url"),
                title=name,
                description=description[:2000] if description else None,
                start_datetime=start_dt,
                end_datetime=end_dt,
                venue_name=venue_name,
                address=address,
                city=city_config.name,
                latitude=lat,
                longitude=lng,
                price_min=price_min,
                price_max=price_max,
                image_url=image_url,
                tags=[category],
                canonical_event_url=raw.get("url"),
                raw_payload=raw,
            )
        except Exception as e:
            logger.warning("eventbrite_parse_error", error=str(e), event_id=raw.get("id"))
            return None

    def _extract_prices(self, raw: dict) -> tuple[Decimal | None, Decimal | None]:
        if raw.get("is_free"):
            return Decimal("0"), Decimal("0")

        ticket = raw.get("ticket_availability") or {}
        price_min = _safe_decimal(
            (ticket.get("minimum_ticket_price") or {}).get("major_value")
        )
        price_max = _safe_decimal(
            (ticket.get("maximum_ticket_price") or {}).get("major_value")
        )
        return price_min, price_max


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_decimal(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None

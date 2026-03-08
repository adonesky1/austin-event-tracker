import asyncio
import re
from datetime import datetime, timezone

import httpx
import structlog
from bs4 import BeautifulSoup

from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter

logger = structlog.get_logger()

CATEGORY_MAP = {
    "music": "music",
    "arts": "arts",
    "film": "arts",
    "theater": "theatre",
    "theatre": "theatre",
    "comedy": "theatre",
    "community": "community",
    "food": "community",
    "sports": "outdoor",
    "kids": "kids",
    "family": "kids",
    "holiday": "seasonal",
    "festival": "festivals",
}

BASE_URL = "https://www.austinchronicle.com"


class AustinChronicleAdapter(SourceAdapter):
    name = "austin_chronicle"
    source_type = SourceType.SCRAPER

    def rate_limit_delay(self) -> float:
        return 2.0

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/events/",
                    headers={"User-Agent": "CityEventsBot/0.1 (family event curator)"},
                )
                response.raise_for_status()
                html = response.text
            except httpx.HTTPError as e:
                logger.error("chronicle_fetch_error", error=str(e))
                return []

        events = self.parse_listings(html)
        logger.info("chronicle_fetch_complete", count=len(events))
        return events

    def parse_listings(self, html: str) -> list[RawEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[RawEvent] = []

        rows = soup.select(".cal-row")
        for row in rows:
            parsed = self._parse_row(row)
            if parsed:
                events.append(parsed)

        return events

    def _parse_row(self, row) -> RawEvent | None:
        try:
            title_el = row.select_one(".cal-title a")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = f"{BASE_URL}{url}"

            venue_el = row.select_one(".cal-venue a, .cal-venue")
            venue_name = venue_el.get_text(strip=True) if venue_el else None

            date_el = row.select_one(".date-num")
            time_el = row.select_one(".cal-time")
            start_dt = self._parse_datetime(
                date_el.get_text(strip=True) if date_el else "",
                time_el.get_text(strip=True) if time_el else "",
            )
            if not start_dt:
                return None

            price_el = row.select_one(".cal-price")
            price_text = price_el.get_text(strip=True).lower() if price_el else ""
            price_min, price_max = self._parse_price(price_text)

            category_el = row.select_one(".cal-category")
            category_text = category_el.get_text(strip=True).lower() if category_el else ""
            category = CATEGORY_MAP.get(category_text, "community")

            desc_el = row.select_one(".cal-description")
            description = desc_el.get_text(strip=True) if desc_el else None

            img_el = row.select_one(".cal-image img")
            image_url = img_el.get("src") if img_el else None

            return RawEvent(
                source_name=self.name,
                source_type=self.source_type.value,
                source_url=url,
                title=title,
                description=description,
                start_datetime=start_dt,
                venue_name=venue_name,
                city="austin",
                price_min=price_min,
                price_max=price_max,
                image_url=image_url,
                tags=[category],
                canonical_event_url=url,
                raw_payload={"html_title": title, "html_venue": venue_name},
            )
        except Exception as e:
            logger.warning("chronicle_parse_row_error", error=str(e))
            return None

    def _parse_datetime(self, date_str: str, time_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            year = datetime.now().year
            clean_time = time_str.split("-")[0].strip() if time_str else "12:00pm"
            dt_str = f"{date_str} {year} {clean_time}"
            dt = datetime.strptime(dt_str, "%b %d %Y %I:%M%p")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                dt_str = f"{date_str} {year}"
                dt = datetime.strptime(dt_str, "%b %d %Y")
                return dt.replace(hour=12, tzinfo=timezone.utc)
            except ValueError:
                return None

    def _parse_price(self, text: str) -> tuple:
        from decimal import Decimal

        if not text or "free" in text:
            return Decimal("0"), Decimal("0")
        numbers = re.findall(r"\$?([\d.]+)", text)
        if len(numbers) >= 2:
            return Decimal(numbers[0]), Decimal(numbers[1])
        elif len(numbers) == 1:
            return Decimal(numbers[0]), Decimal(numbers[0])
        return None, None

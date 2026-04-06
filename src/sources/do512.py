import re
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from bs4 import BeautifulSoup

from src.config.city import CityConfig
from src.models.base import SourceType
from src.schemas.event import RawEvent
from src.sources.base import SourceAdapter

logger = structlog.get_logger()

CATEGORY_MAP = {
    "music": "music",
    "comedy": "theatre",
    "theater": "theatre",
    "theatre": "theatre",
    "family": "kids",
    "kids": "kids",
    "food": "community",
    "drink": "community",
    "sports": "outdoor",
    "fitness": "outdoor",
    "arts": "arts",
    "festival": "festivals",
    "community": "community",
    "nightlife": "music",
}


class Do512Adapter(SourceAdapter):
    name = "do512"
    source_type = SourceType.SCRAPER

    EVENTS_URL = "https://do512.com/events"

    def rate_limit_delay(self) -> float:
        return 3.0

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("do512_playwright_not_installed")
            return []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await ctx.new_page()
                await page.goto(self.EVENTS_URL, wait_until="networkidle", timeout=30000)
                html = await page.content()
                await browser.close()
        except Exception as e:
            logger.error("do512_fetch_error", error=str(e))
            return []

        events = self.parse_listings(html)
        logger.info("do512_fetch_complete", count=len(events))
        return events

    def parse_listings(self, html: str) -> list[RawEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[RawEvent] = []

        listings = soup.select(".ds-listing")
        for listing in listings:
            parsed = self._parse_listing(listing)
            if parsed:
                events.append(parsed)

        return events

    def _parse_listing(self, listing) -> RawEvent | None:
        try:
            title_el = listing.select_one(".ds-listing-event-title-text")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            link_el = listing.select_one("a.ds-listing-event-title")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = f"https://do512.com{url}"

            venue_el = listing.select_one(".ds-listing-venue a, .ds-listing-venue")
            venue_name = venue_el.get_text(strip=True) if venue_el else None

            date_el = listing.select_one(".ds-listing-date")
            time_el = listing.select_one(".ds-listing-time")
            start_dt = self._parse_datetime(
                date_el.get_text(strip=True) if date_el else "",
                time_el.get_text(strip=True) if time_el else "",
            )
            if not start_dt:
                return None

            price_el = listing.select_one(".ds-listing-price")
            price_text = price_el.get_text(strip=True).lower() if price_el else ""
            price_min, price_max = self._parse_price(price_text)

            cat_el = listing.select_one(".ds-listing-category")
            cat_text = cat_el.get_text(strip=True).lower() if cat_el else ""
            category = CATEGORY_MAP.get(cat_text, "community")

            desc_el = listing.select_one(".ds-listing-description")
            description = desc_el.get_text(strip=True) if desc_el else None

            img_el = listing.select_one(".ds-listing-image img")
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
                raw_payload={"event_id": listing.get("data-event-id")},
            )
        except Exception as e:
            logger.warning("do512_parse_listing_error", error=str(e))
            return None

    def _parse_datetime(self, date_str: str, time_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            # "Saturday, March 15, 2026" -> date
            dt = datetime.strptime(date_str, "%A, %B %d, %Y")
            # "2:00 PM - 11:00 PM" -> take start time
            start_time = time_str.split("-")[0].strip() if time_str else ""
            if start_time:
                try:
                    t = datetime.strptime(start_time, "%I:%M %p")
                    dt = dt.replace(hour=t.hour, minute=t.minute)
                except ValueError:
                    pass
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _parse_price(self, text: str) -> tuple:
        if not text or "free" in text:
            return Decimal("0"), Decimal("0")
        numbers = re.findall(r"\$?([\d.]+)", text)
        if len(numbers) >= 2:
            return Decimal(numbers[0]), Decimal(numbers[1])
        elif len(numbers) == 1:
            return Decimal(numbers[0]), Decimal(numbers[0])
        return None, None

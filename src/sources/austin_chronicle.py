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
    "dance": "arts",
    "visual art": "arts",
    "literary": "arts",
}

BASE_URL = "https://calendar.austinchronicle.com"


class AustinChronicleAdapter(SourceAdapter):
    name = "austin_chronicle"
    source_type = SourceType.SCRAPER

    def rate_limit_delay(self) -> float:
        return 2.0

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("chronicle_playwright_not_installed")
            return []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox"],
                )
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await ctx.new_page()
                await page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
                # Wait for event items to appear
                try:
                    await page.wait_for_selector("li.fdn-pres-item", timeout=10000)
                except Exception:
                    pass
                html = await page.content()
                await browser.close()
        except Exception as e:
            logger.error("chronicle_fetch_error", error=str(e))
            return []

        events = self.parse_listings(html)
        logger.info("chronicle_fetch_complete", count=len(events))
        return events

    def parse_listings(self, html: str) -> list[RawEvent]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[RawEvent] = []

        items = soup.select("li.fdn-pres-item")
        for item in items:
            parsed = self._parse_item(item)
            if parsed:
                events.append(parsed)

        return events

    def _parse_item(self, item) -> RawEvent | None:
        try:
            title_el = item.select_one("p.fdn-teaser-headline a")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = f"{BASE_URL}{url}"

            # Image
            img_el = item.select_one(".fdn-event-search-image-block img")
            image_url = img_el.get("src") if img_el else None

            # Date — Foundation platform puts date info in .fdn-event-dates or meta text
            start_dt = self._extract_date(item)
            if not start_dt:
                return None

            # Venue
            venue_el = item.select_one(".fdn-venue-name, .fdn-event-venue, [class*='venue']")
            venue_name = venue_el.get_text(strip=True) if venue_el else None

            # Category
            cat_el = item.select_one(".fdn-event-category, [class*='category']")
            cat_text = cat_el.get_text(strip=True).lower() if cat_el else ""
            category = CATEGORY_MAP.get(cat_text, "community")

            # Description
            desc_el = item.select_one(".fdn-teaser-text, .fdn-event-description, p.uk-margin-remove")
            description = desc_el.get_text(strip=True) if desc_el else None

            # Price
            price_el = item.select_one(".fdn-event-price, [class*='price']")
            price_text = price_el.get_text(strip=True).lower() if price_el else ""
            price_min, price_max = self._parse_price(price_text)

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
            logger.warning("chronicle_parse_item_error", error=str(e))
            return None

    def _extract_date(self, item) -> datetime | None:
        # Try known Foundation date selectors
        for selector in [
            ".fdn-event-dates",
            ".fdn-start-date",
            ".fdn-event-date",
            "[class*='date']",
            ".fdn-teaser-meta",
        ]:
            el = item.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                dt = self._parse_datetime_text(text)
                if dt:
                    return dt

        # Fall back: search all text in item for a date pattern
        full_text = item.get_text(" ", strip=True)
        dt = self._parse_datetime_text(full_text)
        if dt:
            return dt

        # Last resort: use today's date so the event isn't dropped
        return datetime.now(tz=timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    def _parse_datetime_text(self, text: str) -> datetime | None:
        if not text:
            return None
        # "April 5, 2026" or "Apr 5, 2026" or "Saturday, April 5"
        patterns = [
            r"(\w+ \d{1,2},\s*\d{4})",
            r"(\w+day,\s*\w+ \d{1,2},?\s*\d{4})",
            r"(\w+ \d{1,2})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(1).strip()
                for fmt in ["%B %d, %Y", "%b %d, %Y", "%A, %B %d, %Y", "%A, %B %d %Y", "%B %d"]:
                    try:
                        dt = datetime.strptime(raw, fmt)
                        if dt.year == 1900:
                            dt = dt.replace(year=datetime.now().year)
                        return dt.replace(hour=12, tzinfo=timezone.utc)
                    except ValueError:
                        continue
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

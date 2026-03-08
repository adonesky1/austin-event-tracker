from src.schemas.event import NormalizedEvent, RawEvent

CATEGORY_ALIASES = {
    "live music": "music",
    "concert": "music",
    "gallery": "arts",
    "exhibition": "arts",
    "fair": "festivals",
    "fest": "festivals",
    "performance": "theatre",
    "show": "theatre",
    "children": "kids",
    "family": "kids",
    "nature": "outdoor",
    "parks": "outdoor",
    "holiday": "seasonal",
    "market": "community",
    "neighborhood": "community",
}

VALID_CATEGORIES = {"music", "arts", "festivals", "theatre", "kids", "outdoor", "seasonal", "community"}


def normalize_raw_event(raw: RawEvent) -> NormalizedEvent:
    title = raw.title.strip() if raw.title else ""
    city = raw.city.lower().strip() if raw.city else ""
    venue_name = _title_case(raw.venue_name) if raw.venue_name else None

    category = _resolve_category(raw.tags, raw.source_name)

    return NormalizedEvent(
        title=title,
        description=raw.description,
        category=category,
        start_datetime=raw.start_datetime,
        end_datetime=raw.end_datetime,
        venue_name=venue_name,
        address=raw.address,
        neighborhood=raw.neighborhood,
        city=city,
        latitude=raw.latitude,
        longitude=raw.longitude,
        price_min=raw.price_min,
        price_max=raw.price_max,
        currency=raw.currency,
        age_suitability=raw.age_suitability,
        image_url=raw.image_url,
        tags=raw.tags,
        canonical_event_url=raw.canonical_event_url,
        source_name=raw.source_name,
        source_type=raw.source_type,
        source_url=raw.source_url,
    )


def _resolve_category(tags: list[str], source_name: str) -> str:
    for tag in tags:
        t = tag.lower().strip()
        if t in VALID_CATEGORIES:
            return t
        if t in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[t]
    if source_name == "bandsintown":
        return "music"
    return "community"


def _title_case(s: str) -> str:
    words = s.strip().split()
    small_words = {"the", "at", "in", "on", "of", "and", "a", "an", "for", "to"}
    result = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in small_words:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)

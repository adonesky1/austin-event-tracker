from datetime import datetime, timezone, timedelta

from src.schemas.event import NormalizedEvent

MAX_TOP_PICKS = 4
MAX_PER_SECTION = 6
WEEKEND_DAYS_AHEAD = 4
PLAN_AHEAD_MIN_DAYS = 7
FREE_CHEAP_THRESHOLD = 10.0
HIGH_FAMILY_SCORE = 0.65
LOW_FAMILY_SCORE = 0.45
KIDS_CATEGORIES = {"kids", "festivals", "outdoor"}
ADULT_CATEGORIES = {"music", "theatre", "arts"}


def group_events_into_sections(
    events_with_scores: list[tuple[NormalizedEvent, float]],
) -> dict[str, list[tuple[NormalizedEvent, float]]]:
    now = datetime.now(timezone.utc)
    weekend_cutoff = now + timedelta(days=WEEKEND_DAYS_AHEAD)
    plan_ahead_cutoff = now + timedelta(days=PLAN_AHEAD_MIN_DAYS)

    sections: dict[str, list[tuple[NormalizedEvent, float]]] = {
        "top_picks": [],
        "kids_family": [],
        "date_night": [],
        "this_weekend": [],
        "plan_ahead": [],
        "free_cheap": [],
    }

    # Track which events appear in "top" sections to avoid over-repetition
    in_top: set[str] = set()

    # Top picks: highest scored, any type
    for event, score in events_with_scores[:MAX_TOP_PICKS]:
        sections["top_picks"].append((event, score))
        in_top.add(str(event.id))

    # Categorize remaining
    for event, score in events_with_scores:
        eid = str(event.id)
        family_score = event.family_score or 0.5
        days_until = (event.start_datetime - now).days

        # Kids & Family
        if (
            family_score >= HIGH_FAMILY_SCORE
            or event.category in KIDS_CATEGORIES
        ) and len(sections["kids_family"]) < MAX_PER_SECTION:
            sections["kids_family"].append((event, score))

        # Date Night / Adults
        if (
            family_score <= LOW_FAMILY_SCORE
            or event.category in ADULT_CATEGORIES
        ) and len(sections["date_night"]) < MAX_PER_SECTION:
            sections["date_night"].append((event, score))

        # This Weekend
        if (
            event.start_datetime <= weekend_cutoff
            and eid not in in_top
            and len(sections["this_weekend"]) < MAX_PER_SECTION
        ):
            sections["this_weekend"].append((event, score))

        # Plan Ahead
        if (
            days_until >= PLAN_AHEAD_MIN_DAYS
            and eid not in in_top
            and len(sections["plan_ahead"]) < MAX_PER_SECTION
        ):
            sections["plan_ahead"].append((event, score))

        # Free & Cheap
        price = float(event.price_max) if event.price_max is not None else None
        if (
            price is not None
            and price <= FREE_CHEAP_THRESHOLD
            and len(sections["free_cheap"]) < MAX_PER_SECTION
        ):
            sections["free_cheap"].append((event, score))

    # Remove empty sections
    return {k: v for k, v in sections.items() if v}

from datetime import datetime, timezone

from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema

BUDGET_PRICE_LIMITS = {
    "free": 0,
    "low": 20,
    "moderate": 60,
    "any": 9999,
}


def compute_rule_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    scores = {
        "category": _category_score(event, profile),
        "day": _day_score(event, profile),
        "time": _time_score(event, profile),
        "neighborhood": _neighborhood_score(event, profile),
        "budget": _budget_score(event, profile),
        "recency": _recency_score(event),
    }

    weights = {
        "category": 0.30,
        "day": 0.15,
        "time": 0.10,
        "neighborhood": 0.15,
        "budget": 0.20,
        "recency": 0.10,
    }

    total = sum(scores[k] * weights[k] for k in scores)
    return round(min(max(total, 0.0), 1.0), 4)


def _category_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    cat = event.category.lower()
    tags = [t.lower() for t in (event.tags or [])]
    all_cats = {cat} | set(tags)

    interests = {i.lower() for i in (profile.interests or [])}
    dislikes = {d.lower() for d in (profile.dislikes or [])}

    if all_cats & dislikes:
        return 0.0
    if all_cats & interests:
        return 1.0
    return 0.4


def _day_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    preferred = {d.lower() for d in (profile.preferred_days or [])}
    if not preferred:
        return 0.5
    event_day = event.start_datetime.strftime("%A").lower()
    return 1.0 if event_day in preferred else 0.3


def _time_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    preferred = {t.lower() for t in (profile.preferred_times or [])}
    if not preferred:
        return 0.5
    hour = event.start_datetime.hour
    event_time = _hour_to_period(hour)
    return 1.0 if event_time in preferred else 0.3


def _hour_to_period(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    return "night"


def _neighborhood_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    preferred = {n.lower() for n in (profile.preferred_neighborhoods or [])}
    if not preferred:
        return 0.5
    event_neighborhood = (event.neighborhood or "").lower()
    event_venue = (event.venue_name or "").lower()
    for n in preferred:
        if n in event_neighborhood or n in event_venue:
            return 1.0
    return 0.4


def _budget_score(event: NormalizedEvent, profile: UserProfileSchema) -> float:
    limit = BUDGET_PRICE_LIMITS.get(profile.budget, 60)
    price = event.price_max

    if price is None:
        return 0.6  # unknown price, give neutral score

    price_float = float(price)
    if price_float == 0:
        return 1.0
    if price_float <= limit:
        return 0.8
    if price_float <= limit * 1.5:
        return 0.5
    return 0.1


def _recency_score(event: NormalizedEvent) -> float:
    now = datetime.now(timezone.utc)
    days_away = (event.start_datetime - now).days
    if days_away < 0:
        return 0.0
    elif days_away <= 3:
        return 1.0
    elif days_away <= 7:
        return 0.8
    elif days_away <= 14:
        return 0.6
    return 0.4

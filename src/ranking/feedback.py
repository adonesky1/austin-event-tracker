from datetime import datetime, timezone, timedelta

from src.models.base import FeedbackType
from src.schemas.event import NormalizedEvent

# How much each feedback type adjusts the score
FEEDBACK_ADJUSTMENTS = {
    FeedbackType.THUMBS_UP: +0.15,
    FeedbackType.MORE_LIKE_THIS: +0.20,
    FeedbackType.THUMBS_DOWN: -0.15,
    FeedbackType.LESS_LIKE_THIS: -0.20,
    FeedbackType.TOO_FAR: -0.10,
    FeedbackType.TOO_EXPENSIVE: -0.10,
    FeedbackType.WRONG_AGE: -0.10,
    FeedbackType.ALREADY_KNEW: -0.05,
}

RECENCY_WEIGHT_DAYS = 30  # feedback older than this gets 0.5x weight


def adjust_score_for_feedback(
    base_score: float,
    event: NormalizedEvent,
    feedback_history: list[dict],
) -> float:
    if not feedback_history:
        return base_score

    adjustment = 0.0
    now = datetime.now(timezone.utc)

    for fb in feedback_history:
        if not _is_similar_event(event, fb):
            continue

        delta = FEEDBACK_ADJUSTMENTS.get(fb["feedback_type"], 0.0)

        # Weight recent feedback more heavily
        fb_date = fb.get("created_at")
        if fb_date:
            age_days = (now - fb_date).days
            weight = 1.0 if age_days <= RECENCY_WEIGHT_DAYS else 0.5
        else:
            weight = 1.0

        adjustment += delta * weight

    new_score = base_score + adjustment
    return round(min(max(new_score, 0.0), 1.0), 4)


def _is_similar_event(event: NormalizedEvent, fb: dict) -> bool:
    # Match on category and/or neighborhood/venue
    event_cat = event.category.lower()
    fb_cat = (fb.get("event_category") or "").lower()
    cat_match = event_cat == fb_cat

    event_neighborhood = (event.neighborhood or "").lower()
    event_venue = (event.venue_name or "").lower()
    fb_neighborhood = (fb.get("event_neighborhood") or "").lower()
    location_match = fb_neighborhood and (
        fb_neighborhood in event_neighborhood or fb_neighborhood in event_venue
    )

    return cat_match or location_match

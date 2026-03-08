from datetime import datetime

from Levenshtein import ratio as levenshtein_ratio


def title_similarity(a: str, b: str) -> float:
    return levenshtein_ratio(a.lower().strip(), b.lower().strip())


def venue_similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return levenshtein_ratio(a.lower().strip(), b.lower().strip())


def datetime_proximity(a: datetime, b: datetime) -> float:
    diff_hours = abs((a - b).total_seconds()) / 3600
    if diff_hours <= 2:
        return 1.0
    elif diff_hours <= 6:
        return 0.5
    return 0.0


def combined_similarity(event_a, event_b) -> float:
    title_sim = title_similarity(event_a.title, event_b.title)
    venue_sim = venue_similarity(event_a.venue_name, event_b.venue_name)
    time_sim = datetime_proximity(event_a.start_datetime, event_b.start_datetime)
    return 0.5 * title_sim + 0.3 * venue_sim + 0.2 * time_sim

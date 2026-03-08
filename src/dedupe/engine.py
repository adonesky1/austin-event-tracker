import uuid

import structlog

from src.dedupe.similarity import combined_similarity
from src.schemas.event import NormalizedEvent

logger = structlog.get_logger()

FUZZY_AUTO_MERGE_THRESHOLD = 0.80
FUZZY_LLM_THRESHOLD = 0.60


class DedupeEngine:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def deduplicate(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        # Pass 1: exact match on canonical URL
        events = self._dedupe_by_url(events)

        # Pass 2: exact match on (normalized title + venue + date)
        events = self._dedupe_by_title_venue_date(events)

        # Pass 3: fuzzy match with optional LLM tiebreaker
        events = self._dedupe_fuzzy(events)

        return events

    def _dedupe_by_url(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        seen_urls: dict[str, NormalizedEvent] = {}
        result: list[NormalizedEvent] = []

        for event in events:
            url = event.canonical_event_url
            if not url:
                result.append(event)
                continue
            if url in seen_urls:
                self._merge_sources(seen_urls[url], event)
                logger.debug("dedupe_exact_url", title=event.title)
            else:
                seen_urls[url] = event
                result.append(event)

        return result

    def _dedupe_by_title_venue_date(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        seen: dict[str, NormalizedEvent] = {}
        result: list[NormalizedEvent] = []

        for event in events:
            key = self._exact_key(event)
            if key in seen:
                self._merge_sources(seen[key], event)
                logger.debug("dedupe_exact_tvd", title=event.title)
            else:
                seen[key] = event
                result.append(event)

        return result

    def _dedupe_fuzzy(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        merged = [False] * len(events)
        result: list[NormalizedEvent] = []

        for i, event_a in enumerate(events):
            if merged[i]:
                continue
            for j, event_b in enumerate(events):
                if i >= j or merged[j]:
                    continue
                score = combined_similarity(event_a, event_b)
                if score >= FUZZY_AUTO_MERGE_THRESHOLD:
                    winner = self._pick_richer(event_a, event_b)
                    group_id = winner.dedupe_group_id or uuid.uuid4()
                    winner.dedupe_group_id = group_id
                    merged[j] = True
                    logger.debug(
                        "dedupe_fuzzy_merge",
                        score=round(score, 3),
                        a=event_a.title,
                        b=event_b.title,
                    )
                elif score >= FUZZY_LLM_THRESHOLD and self.llm_client:
                    # Async LLM tiebreaker - run synchronously in this context
                    # In production this would be called from an async context
                    pass

            if not merged[i]:
                result.append(event_a)

        return result

    def _exact_key(self, event: NormalizedEvent) -> str:
        title = event.title.lower().strip()
        venue = (event.venue_name or "").lower().strip()
        date = event.start_datetime.strftime("%Y-%m-%d")
        return f"{title}|{venue}|{date}"

    def _pick_richer(self, a: NormalizedEvent, b: NormalizedEvent) -> NormalizedEvent:
        def richness(e: NormalizedEvent) -> int:
            score = 0
            if e.description:
                score += 2
            if e.image_url:
                score += 1
            if e.price_min is not None:
                score += 1
            if e.latitude:
                score += 1
            if e.neighborhood:
                score += 1
            return score

        return a if richness(a) >= richness(b) else b

    def _merge_sources(self, winner: NormalizedEvent, loser: NormalizedEvent):
        # Enrich winner with any fields the loser has that winner lacks
        if not winner.description and loser.description:
            winner.description = loser.description
        if not winner.image_url and loser.image_url:
            winner.image_url = loser.image_url
        if winner.price_min is None and loser.price_min is not None:
            winner.price_min = loser.price_min
            winner.price_max = loser.price_max
        if not winner.latitude and loser.latitude:
            winner.latitude = loser.latitude
            winner.longitude = loser.longitude

        group_id = winner.dedupe_group_id or uuid.uuid4()
        winner.dedupe_group_id = group_id

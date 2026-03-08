import json

import structlog

from src.llm.base import LLMClient
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema

logger = structlog.get_logger()

SYNTHESIS_SYSTEM_PROMPT = """You are an expert local events curator helping a family find the best Austin events.
Your job is to evaluate events for family relevance and write brief editorial summaries.

CRITICAL RULES:
- Never invent or fabricate dates, venues, prices, or any factual details
- Only assess what is provided in the event data
- Be warm, concise, and genuinely helpful
- family_score should reflect how suitable this is for a family with children
- If event data is sparse, note low confidence in your assessment

Always return valid JSON matching the exact schema requested."""

SYNTHESIS_USER_PROMPT = """Family profile:
- Adults: {adults}
- Children ages: {children_ages}
- Interests: {interests}
- Preferred neighborhoods: {neighborhoods}
- Budget: {budget}

Evaluate these {count} events and return a JSON object with an "events" array.
Each item must have these exact fields:
- index (int): matches the input index
- family_score (float 0-1): how suitable for this family (1.0 = perfect fit)
- editorial_summary (str): 1-2 sentence description of the event, enthusiastic but honest
- relevance_explanation (str): 1 sentence explaining why it fits THIS family specifically
- age_suitability (str): e.g. "all ages", "5+", "teens and adults", "21+"

Events:
{events_json}"""


class EventSynthesizer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def enrich_events(
        self,
        events: list[NormalizedEvent],
        profile: UserProfileSchema,
        batch_size: int = 15,
    ) -> list[NormalizedEvent]:
        if not events:
            return events

        enriched = list(events)

        for start in range(0, len(events), batch_size):
            batch = events[start : start + batch_size]
            try:
                results = await self._enrich_batch(batch, profile)
                for item in results:
                    idx = item.get("index", -1)
                    if 0 <= idx < len(batch):
                        event = enriched[start + idx]
                        event.family_score = _clamp(item.get("family_score", 0.5))
                        summary = item.get("editorial_summary")
                        if summary:
                            event.editorial_summary = summary[:500]
                        explanation = item.get("relevance_explanation")
                        if explanation:
                            event.relevance_explanation = explanation[:300]
                        age = item.get("age_suitability")
                        if age and not event.age_suitability:
                            event.age_suitability = age
            except Exception as e:
                logger.error("synthesis_batch_failed", error=str(e), batch_start=start)

        return enriched

    async def _enrich_batch(
        self, events: list[NormalizedEvent], profile: UserProfileSchema
    ) -> list[dict]:
        children_ages = [str(c.get("age", "?")) for c in (profile.children or [])]
        adults_count = len(profile.adults or [{"age": 35}])

        events_data = [
            {
                "index": i,
                "title": e.title,
                "description": (e.description or "")[:300],
                "category": e.category,
                "venue_name": e.venue_name or "TBD",
                "neighborhood": e.neighborhood or "",
                "start_datetime": e.start_datetime.isoformat(),
                "price_min": float(e.price_min) if e.price_min is not None else None,
                "price_max": float(e.price_max) if e.price_max is not None else None,
                "tags": e.tags,
            }
            for i, e in enumerate(events)
        ]

        prompt = SYNTHESIS_USER_PROMPT.format(
            adults=f"{adults_count} adult(s)",
            children_ages=", ".join(children_ages) if children_ages else "no children",
            interests=", ".join(profile.interests or []),
            neighborhoods=", ".join(profile.preferred_neighborhoods or []),
            budget=profile.budget,
            count=len(events),
            events_json=json.dumps(events_data, indent=2),
        )

        response = await self.llm_client.complete_json(prompt, system=SYNTHESIS_SYSTEM_PROMPT)
        return response.get("events", [])


def _clamp(val, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(val)))
    except (TypeError, ValueError):
        return 0.5

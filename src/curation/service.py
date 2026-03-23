from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import structlog
from src.admin.service import get_or_create_profile, list_tracked_items
from src.config.city import load_city_config
from src.config.settings import Settings
from src.curation.profile import build_default_profile, user_profile_to_schema
from src.dedupe.engine import DedupeEngine
from src.ingestion.pipeline import IngestionPipeline
from src.jobs.ingest_job import build_registry
from src.llm.anthropic import AnthropicLLMClient
from src.llm.prompt_loader import get_effective_synthesis_prompts
from src.llm.synthesis import (
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT,
    EventSynthesizer,
)
from src.models.database import create_engine, create_session_factory
from src.ranking.engine import RankingEngine
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema

logger = structlog.get_logger()


@dataclass
class CurationResult:
    profile: UserProfileSchema
    generated_at: datetime
    ranked_events: list[tuple[NormalizedEvent, float]]

    def select_calendar_candidates(
        self,
        min_score: float,
        horizon_days: int,
        now: datetime | None = None,
    ) -> list[tuple[NormalizedEvent, float]]:
        return _filter_ranked_events(
            self.ranked_events,
            min_score=min_score,
            horizon_days=horizon_days,
            now=now or self.generated_at,
        )

    def select_digest_candidates(
        self,
        max_events: int,
        horizon_days: int = 21,
        now: datetime | None = None,
    ) -> list[tuple[NormalizedEvent, float]]:
        selected = _filter_ranked_events(
            self.ranked_events,
            min_score=0.0,
            horizon_days=horizon_days,
            now=now or self.generated_at,
        )
        return selected[:max_events]


class CurationService:
    def __init__(
        self,
        settings: Settings,
        now_provider=None,
    ):
        self.settings = settings
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    async def curate(
        self,
        profile: UserProfileSchema | None = None,
    ) -> CurationResult:
        tracked_items = []
        system_prompt = None
        user_prompt_template = None

        if profile is None:
            engine = None
            try:
                engine = create_engine(self.settings)
                Session = create_session_factory(engine)
                async with Session() as session:
                    db_profile = await get_or_create_profile(session, self.settings)
                    profile = user_profile_to_schema(db_profile)
                    tracked_items = await list_tracked_items(session)
                    system_prompt, user_prompt_template = await get_effective_synthesis_prompts(
                        session
                    )
            except Exception as exc:
                logger.error("curation_db_profile_load_failed", error=str(exc))
                profile = build_default_profile(self.settings)
            finally:
                if engine is not None:
                    await engine.dispose()

        profile = profile or build_default_profile(self.settings)
        city_config = load_city_config(profile.city or self.settings.default_city)
        registry = build_registry(self.settings)
        pipeline = IngestionPipeline(registry=registry, db_session=None)

        ingested = await pipeline.ingest(city_config, persist=False)
        deduped = DedupeEngine(llm_client=None).deduplicate(ingested)
        enriched = await self._enrich_events(
            deduped,
            profile,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )
        ranked = await RankingEngine().rank_events(enriched, profile, tracked_items=tracked_items)

        return CurationResult(
            profile=profile,
            generated_at=self.now_provider(),
            ranked_events=ranked,
        )

    async def _enrich_events(
        self,
        events: list[NormalizedEvent],
        profile: UserProfileSchema,
        system_prompt: str | None = None,
        user_prompt_template: str | None = None,
    ) -> list[NormalizedEvent]:
        if not events:
            return events

        if not self.settings.anthropic_api_key:
            logger.warning("curation_enrichment_skipped_no_anthropic_key", events=len(events))
            return events

        client = AnthropicLLMClient(api_key=self.settings.anthropic_api_key)
        synthesizer = EventSynthesizer(
            llm_client=client,
            system_prompt=system_prompt or SYNTHESIS_SYSTEM_PROMPT,
            user_prompt_template=user_prompt_template or SYNTHESIS_USER_PROMPT,
        )
        return await synthesizer.enrich_events(events, profile)


def _filter_ranked_events(
    events_with_scores: list[tuple[NormalizedEvent, float]],
    min_score: float,
    horizon_days: int,
    now: datetime,
) -> list[tuple[NormalizedEvent, float]]:
    cutoff = now + timedelta(days=horizon_days)
    selected: list[tuple[NormalizedEvent, float]] = []

    for event, score in events_with_scores:
        if event.start_datetime < now:
            continue
        if event.start_datetime > cutoff:
            continue
        if score < min_score:
            continue
        selected.append((event, score))

    return selected

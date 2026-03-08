from datetime import datetime, timezone, timedelta

import structlog

from src.config.settings import Settings
from src.digest.generator import DigestGenerator
from src.llm.anthropic import AnthropicLLMClient
from src.llm.synthesis import EventSynthesizer
from src.notifications.email import EmailChannel
from src.ranking.engine import RankingEngine
from src.schemas.user import UserProfileSchema

logger = structlog.get_logger()

# Austin family profile - loaded from config in production
# TODO: load from user_profiles table when db is wired
DEFAULT_PROFILE = UserProfileSchema(
    email="",  # set from FROM_EMAIL env
    city="austin",
    adults=[{"age": 35}, {"age": 35}],
    children=[{"age": 5}, {"age": 8}],
    preferred_neighborhoods=["South Austin", "Zilker", "East Austin", "Downtown"],
    max_distance_miles=30,
    preferred_days=["saturday", "sunday", "friday"],
    preferred_times=["morning", "afternoon", "evening"],
    budget="moderate",
    interests=["music", "outdoor", "festivals", "kids", "arts", "seasonal", "community"],
    dislikes=[],
    max_events_per_digest=15,
    crowd_sensitivity="medium",
)


async def run_digest():
    settings = Settings()
    profile = DEFAULT_PROFILE.model_copy(update={"email": settings.from_email})

    # In production: query events from db for next 2-3 weeks
    # For now, this is the wiring scaffold
    from src.jobs.ingest_job import run_ingestion
    events = await run_ingestion()

    if not events:
        logger.warning("digest_job_no_events")
        return

    # LLM enrichment on top candidates
    llm_client = AnthropicLLMClient(api_key=settings.anthropic_api_key)
    synthesizer = EventSynthesizer(llm_client=llm_client)
    engine = RankingEngine(llm_client=llm_client)

    pre_ranked = await engine.rank_events(events, profile)
    top_candidates = [e for e, _ in pre_ranked[:30]]
    enriched = await synthesizer.enrich_events(top_candidates, profile)

    final_ranked = await engine.rank_events(enriched, profile)
    top_events = final_ranked[:profile.max_events_per_digest]

    # Generate digest
    now = datetime.now(timezone.utc)
    window_start = now.strftime("%b %-d")
    window_end = (now + timedelta(weeks=3)).strftime("%b %-d")

    generator = DigestGenerator(
        base_url=settings.base_url,
        feedback_secret=settings.feedback_secret,
    )
    html = generator.render_html(top_events, window_start=window_start, window_end=window_end)
    text = generator.render_plaintext(top_events, window_start=window_start, window_end=window_end)
    subject = generator.generate_subject(window_start, window_end)

    # Send
    channel = EmailChannel(api_key=settings.resend_api_key, from_email=settings.from_email)
    result = await channel.send(
        to=profile.email,
        subject=subject,
        html=html,
        text=text,
    )

    logger.info("digest_job_complete", events=len(top_events), email_id=result.get("id"))

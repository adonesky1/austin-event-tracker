from datetime import timedelta

import structlog

from src.config.settings import Settings
from src.curation.service import CurationService
from src.digest.generator import DigestGenerator
from src.notifications.email import EmailChannel
from src.notifications.telegram import TelegramChannel

logger = structlog.get_logger()


async def run_digest():
    settings = Settings()
    curation = CurationService(settings)
    result = await curation.curate()
    top_events = result.select_digest_candidates(
        max_events=result.profile.max_events_per_digest,
        horizon_days=settings.google_calendar_horizon_days,
    )

    if not top_events:
        logger.warning("digest_job_no_events")
        return

    window_start = result.generated_at.strftime("%b %-d")
    window_end = (result.generated_at + timedelta(days=settings.google_calendar_horizon_days)).strftime(
        "%b %-d"
    )

    generator = DigestGenerator(
        base_url=settings.base_url,
        feedback_secret=settings.feedback_secret,
    )
    html = generator.render_html(top_events, window_start=window_start, window_end=window_end)
    text = generator.render_plaintext(top_events, window_start=window_start, window_end=window_end)
    subject = generator.generate_subject(window_start, window_end)

    if settings.telegram_bot_token and settings.telegram_chat_id:
        channel = TelegramChannel(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
    else:
        channel = EmailChannel(api_key=settings.resend_api_key, from_email=settings.from_email)
    send_result = await channel.send(
        to=result.profile.email,
        subject=subject,
        html=html,
        text=text,
    )

    logger.info(
        "digest_job_complete",
        events=len(top_events),
        email_id=send_result.get("id"),
    )

import uuid
from datetime import timedelta, timezone, datetime

import structlog

from src.config.settings import Settings
from src.curation.service import CurationService
from src.digest.generator import DigestGenerator
from src.models.base import DigestStatus
from src.models.database import create_engine, create_session_factory
from src.models.digest import Digest
from src.notifications.email import EmailChannel
from src.notifications.telegram import TelegramChannel

logger = structlog.get_logger()


async def run_digest():
    try:
        await _run_digest()
    except Exception as exc:
        logger.error("digest_job_failed", error=str(exc))
        from src.notifications.error_notifier import notify_job_failure
        await notify_job_failure("digest", exc)
        raise


async def _run_digest():
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

    digest_id = uuid.uuid4()
    await _save_digest(
        settings=settings,
        digest_id=digest_id,
        user_id=result.profile.id,
        subject=subject,
        html=html,
        text=text,
        event_ids=[e.id for e in top_events],
        window_start=result.generated_at.date(),
        window_end=(result.generated_at + timedelta(days=settings.google_calendar_horizon_days)).date(),
        status=DigestStatus.DRAFT,
    )

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

    await _update_digest_status(settings, digest_id, DigestStatus.SENT)

    logger.info(
        "digest_job_complete",
        events=len(top_events),
        email_id=send_result.get("id"),
    )


async def _save_digest(
    settings: Settings,
    digest_id: uuid.UUID,
    user_id: uuid.UUID,
    subject: str,
    html: str,
    text: str,
    event_ids: list,
    window_start,
    window_end,
    status: DigestStatus,
):
    try:
        engine = create_engine(settings)
        Session = create_session_factory(engine)
        async with Session() as session:
            session.add(
                Digest(
                    id=digest_id,
                    user_id=user_id,
                    subject=subject,
                    html_content=html,
                    plaintext_content=text,
                    event_ids=event_ids,
                    status=status,
                    window_start=window_start,
                    window_end=window_end,
                )
            )
            await session.commit()
        await engine.dispose()
    except Exception as exc:
        logger.error("digest_save_failed", error=str(exc))


async def _update_digest_status(settings: Settings, digest_id: uuid.UUID, status: DigestStatus):
    from sqlalchemy import update as sa_update
    try:
        engine = create_engine(settings)
        Session = create_session_factory(engine)
        async with Session() as session:
            await session.execute(
                sa_update(Digest)
                .where(Digest.id == digest_id)
                .values(
                    status=status,
                    sent_at=datetime.now(timezone.utc) if status == DigestStatus.SENT else None,
                )
            )
            await session.commit()
        await engine.dispose()
    except Exception as exc:
        logger.error("digest_status_update_failed", error=str(exc))

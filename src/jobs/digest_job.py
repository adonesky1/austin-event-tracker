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
    digest_id = uuid.uuid4()
    html = generator.render_html(
        top_events,
        window_start=window_start,
        window_end=window_end,
        digest_id=str(digest_id),
    )
    text = generator.render_plaintext(
        top_events,
        window_start=window_start,
        window_end=window_end,
        digest_id=str(digest_id),
    )
    subject = generator.generate_subject(window_start, window_end)

    digest_saved = False
    if result.profile.id is None:
        logger.warning("digest_save_skipped_missing_profile_id", email=result.profile.email)
    else:
        digest_saved = await _save_digest(
            settings=settings,
            digest_id=digest_id,
            user_id=result.profile.id,
            subject=subject,
            html=html,
            text=text,
            event_ids=[event.id for event, _score in top_events],
            window_start=result.generated_at.date(),
            window_end=(
                result.generated_at + timedelta(days=settings.google_calendar_horizon_days)
            ).date(),
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

    if digest_saved:
        await _update_digest_status(settings, digest_id, DigestStatus.SENT)

    logger.info(
        "digest_job_complete",
        events=len(top_events),
        email_id=send_result.get("id"),
    )
    return {
        "status": "success",
        "summary": f"Sent digest with {len(top_events)} events.",
        "digest_id": str(digest_id),
        "event_count": len(top_events),
        "delivery_id": send_result.get("id"),
        "saved_to_db": digest_saved,
    }


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
) -> bool:
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
        return True
    except Exception as exc:
        logger.error("digest_save_failed", error=str(exc))
        return False


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

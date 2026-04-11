from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from src.config.settings import Settings
from src.curation.service import CurationService
from src.integrations.calendar import GoogleCalendarIntegration
from src.models.calendar_sync import CalendarSyncRun
from src.models.base import SyncRunStatus
from src.models.database import create_engine, create_session_factory

logger = structlog.get_logger()


async def preview_google_calendar_sync() -> dict:
    settings = Settings()
    _ensure_google_calendar_enabled(settings)

    curation = CurationService(settings)
    result = await curation.curate()
    candidates = result.select_calendar_candidates(
        min_score=settings.google_calendar_min_score,
        horizon_days=settings.google_calendar_horizon_days,
    )

    integration = GoogleCalendarIntegration(settings)
    preview = await integration.preview_sync(candidates, result.profile)
    payload = preview.to_dict()
    payload["summary"] = (
        f"Preview selected {preview.selected_count} events: "
        f"{preview.created_count} create, {preview.updated_count} update, {preview.deleted_count} delete."
    )
    return payload


async def run_google_calendar_sync(trigger: str = "scheduler") -> dict:
    settings = Settings()
    if not settings.google_calendar_enabled:
        logger.info("google_calendar_sync_skipped_disabled")
        return {
            "status": "skipped",
            "trigger": trigger,
            "reason": "Google Calendar sync is disabled",
            "summary": "Google Calendar sync is disabled.",
        }

    started_at = datetime.now(timezone.utc)
    try:
        curation = CurationService(settings)
        result = await curation.curate()
        candidates = result.select_calendar_candidates(
            min_score=settings.google_calendar_min_score,
            horizon_days=settings.google_calendar_horizon_days,
        )
        integration = GoogleCalendarIntegration(settings)
        sync_result = await integration.sync_events(
            candidates,
            result.profile,
            trigger=trigger,
        )
        payload = sync_result.to_dict()
        payload["summary"] = (
            f"Synced {sync_result.selected_count} events: "
            f"{sync_result.created_count} created, {sync_result.updated_count} updated, "
            f"{sync_result.deleted_count} deleted."
        )
        await _persist_sync_run(
            settings=settings,
            trigger=trigger,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            payload=payload,
        )
        logger.info(
            "google_calendar_sync_complete",
            selected=sync_result.selected_count,
            created=sync_result.created_count,
            updated=sync_result.updated_count,
            deleted=sync_result.deleted_count,
        )
        return payload
    except Exception as exc:
        logger.error("google_calendar_sync_failed", error=str(exc))
        from src.notifications.error_notifier import notify_job_failure
        await notify_job_failure("google_calendar_sync", exc)
        payload = {
            "status": "failed",
            "trigger": trigger,
            "dry_run": False,
            "window_start": started_at.date(),
            "window_end": started_at.date(),
            "selected_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "deleted_count": 0,
            "error": str(exc),
            "selected_events": [],
            "summary": "Google Calendar sync failed.",
        }
        await _persist_sync_run(
            settings=settings,
            trigger=trigger,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            payload=payload,
        )
        raise


async def get_latest_calendar_sync_status() -> dict:
    settings = Settings()

    latest = None
    try:
        engine = create_engine(settings)
        Session = create_session_factory(engine)
        async with Session() as session:
            result = await session.execute(
                select(CalendarSyncRun).order_by(CalendarSyncRun.started_at.desc()).limit(1)
            )
            latest = result.scalar_one_or_none()
        await engine.dispose()
    except Exception as exc:
        logger.error("google_calendar_status_query_failed", error=str(exc))

    latest_payload = None
    if latest is not None:
        latest_payload = {
            "id": str(latest.id),
            "trigger": latest.trigger,
            "status": latest.status.value,
            "started_at": latest.started_at.isoformat(),
            "completed_at": latest.completed_at.isoformat() if latest.completed_at else None,
            "window_start": latest.window_start.isoformat(),
            "window_end": latest.window_end.isoformat(),
            "selected_count": latest.selected_count,
            "created_count": latest.created_count,
            "updated_count": latest.updated_count,
            "deleted_count": latest.deleted_count,
            "error": latest.error,
        }

    return {
        "enabled": settings.google_calendar_enabled,
        "calendar_id": settings.google_calendar_id,
        "calendar_name": settings.google_calendar_calendar_name,
        "min_score": settings.google_calendar_min_score,
        "horizon_days": settings.google_calendar_horizon_days,
        "sync_hour": settings.google_calendar_sync_hour,
        "timezone": settings.google_calendar_timezone,
        "latest_run": latest_payload,
    }


async def _persist_sync_run(
    settings: Settings,
    trigger: str,
    started_at: datetime,
    completed_at: datetime,
    payload: dict,
):
    try:
        engine = create_engine(settings)
        Session = create_session_factory(engine)
        async with Session() as session:
            session.add(
                CalendarSyncRun(
                    trigger=trigger,
                    status=_map_status(payload.get("status")),
                    started_at=started_at,
                    completed_at=completed_at,
                    window_start=payload["window_start"],
                    window_end=payload["window_end"],
                    selected_count=payload.get("selected_count", 0),
                    created_count=payload.get("created_count", 0),
                    updated_count=payload.get("updated_count", 0),
                    deleted_count=payload.get("deleted_count", 0),
                    error=payload.get("error"),
                )
            )
            await session.commit()
        await engine.dispose()
    except Exception as exc:
        logger.error("google_calendar_sync_persist_failed", error=str(exc))


def _map_status(value: str | None) -> SyncRunStatus:
    if value == "failed":
        return SyncRunStatus.FAILED
    if value == "skipped":
        return SyncRunStatus.SKIPPED
    return SyncRunStatus.SUCCESS


def _ensure_google_calendar_enabled(settings: Settings):
    if not settings.google_calendar_enabled:
        raise RuntimeError("Google Calendar sync is disabled")

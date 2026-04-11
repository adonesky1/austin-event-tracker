import asyncio
import inspect
import traceback
import uuid
from typing import Awaitable, Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import Settings
from src.jobs.calendar_sync_job import run_google_calendar_sync
from src.jobs.cleanup_job import cleanup_old_events
from src.jobs.digest_job import run_digest
from src.jobs.ingest_job import run_ingestion
from src.jobs.job_run_store import create_job_run_record, update_job_run_record
from src.jobs.runtime_status import (
    get_job_runtime_snapshot,
    is_job_active,
    mark_job_complete,
    mark_job_failed,
    mark_job_queued,
    mark_job_running,
    register_job,
)

logger = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None
_job_runners: dict[str, Callable[[], Awaitable[object]]] = {}
_job_names: dict[str, str] = {}


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def create_scheduler(start: bool = True) -> AsyncIOScheduler:
    global _scheduler
    settings = Settings()
    scheduler = AsyncIOScheduler(timezone="America/Chicago")

    _add_tracked_job(
        scheduler,
        runner=run_ingestion,
        trigger=CronTrigger(hour=6, timezone="America/Chicago"),
        id="ingest_all_sources",
        name="Ingest all sources",
    )

    _add_tracked_job(
        scheduler,
        runner=run_digest,
        trigger=CronTrigger(day_of_week="tue,fri", hour=8, timezone="America/Chicago"),
        id="generate_and_send_digest",
        name="Generate and send digest",
    )

    _add_tracked_job(
        scheduler,
        runner=run_google_calendar_sync,
        trigger=CronTrigger(
            hour=settings.google_calendar_sync_hour,
            timezone=settings.google_calendar_timezone,
        ),
        id="sync_google_calendar",
        name="Sync Google Calendar",
    )

    _add_tracked_job(
        scheduler,
        runner=cleanup_old_events,
        trigger=CronTrigger(day_of_week="sun", hour=3, timezone="America/Chicago"),
        id="cleanup_old_events",
        name="Archive old events",
    )

    _scheduler = scheduler

    if start:
        scheduler.start()
        logger.info("scheduler_started", jobs=[j.id for j in scheduler.get_jobs()])

    return scheduler


def trigger_job_now(job_id: str) -> dict:
    scheduler = get_scheduler()
    if scheduler is None:
        raise RuntimeError("Scheduler not initialised")

    job = scheduler.get_job(job_id)
    if job is None:
        raise RuntimeError(f"Job '{job_id}' not found")

    name = _job_names.get(job_id, job.name)
    if is_job_active(job_id):
        raise RuntimeError(f"Job '{name}' is already running")

    mark_job_queued(job_id, name, "manual")
    asyncio.create_task(_run_registered_job(job_id, trigger="manual"))
    return get_job_runtime_snapshot(job_id, name)


async def apply_db_schedule_overrides() -> None:
    """Load any persisted schedule overrides from DB and apply them. Call after startup."""
    scheduler = get_scheduler()
    if scheduler is None:
        return
    settings = Settings()
    try:
        await _load_and_apply_overrides(scheduler, settings)
    except Exception as exc:
        logger.warning("scheduler_db_override_failed", error=str(exc))


async def _load_and_apply_overrides(scheduler: AsyncIOScheduler, settings: Settings) -> None:
    from sqlalchemy import select
    from src.models.database import create_engine, create_session_factory
    from src.models.job_schedule import JobSchedule

    engine = create_engine(settings)
    Session = create_session_factory(engine)
    try:
        async with Session() as session:
            rows = (await session.execute(select(JobSchedule))).scalars().all()
            for row in rows:
                _apply_schedule(scheduler, row.job_id, row.day_of_week, row.hour)
                logger.info("scheduler_override_applied", job_id=row.job_id, hour=row.hour)
    finally:
        await engine.dispose()


def _apply_schedule(
    scheduler: AsyncIOScheduler, job_id: str, day_of_week: str | None, hour: int
) -> None:
    job = scheduler.get_job(job_id)
    if job is None:
        logger.warning("scheduler_job_not_found", job_id=job_id)
        return
    trigger_kwargs: dict = {"hour": hour, "timezone": "America/Chicago"}
    if day_of_week:
        trigger_kwargs["day_of_week"] = day_of_week
    job.reschedule(trigger=CronTrigger(**trigger_kwargs))


async def reschedule_job(job_id: str, day_of_week: str | None, hour: int) -> None:
    """Update a job's schedule in-memory and persist to DB."""
    from sqlalchemy.dialects.postgresql import insert
    from src.models.database import create_engine, create_session_factory
    from src.models.job_schedule import JobSchedule

    scheduler = get_scheduler()
    if scheduler is None:
        raise RuntimeError("Scheduler not initialised")

    _apply_schedule(scheduler, job_id, day_of_week, hour)

    settings = Settings()
    engine = create_engine(settings)
    Session = create_session_factory(engine)
    try:
        async with Session() as session:
            stmt = (
                insert(JobSchedule)
                .values(job_id=job_id, day_of_week=day_of_week, hour=hour)
                .on_conflict_do_update(
                    index_elements=["job_id"],
                    set_={"day_of_week": day_of_week, "hour": hour, "updated_at": __import__("sqlalchemy").func.now()},
                )
            )
            await session.execute(stmt)
            await session.commit()
    finally:
        await engine.dispose()

    logger.info("job_rescheduled", job_id=job_id, day_of_week=day_of_week, hour=hour)


def _add_tracked_job(
    scheduler: AsyncIOScheduler,
    *,
    runner: Callable[[], Awaitable[object]],
    trigger,
    id: str,
    name: str,
) -> None:
    _job_runners[id] = runner
    _job_names[id] = name
    register_job(id, name)
    scheduler.add_job(
        _run_registered_job,
        trigger,
        args=[id],
        id=id,
        name=name,
        replace_existing=True,
    )


async def _run_registered_job(job_id: str, trigger: str = "scheduler"):
    runner = _job_runners.get(job_id)
    name = _job_names.get(job_id, job_id)
    if runner is None:
        raise RuntimeError(f"No runner registered for job '{job_id}'")

    run_state = mark_job_running(job_id, name, trigger)
    run_id = await _create_persisted_job_run(job_id, name, trigger, run_state)
    try:
        result = await _invoke_runner(runner, trigger)
    except Exception as exc:
        run_state = mark_job_failed(
            job_id,
            name,
            trigger,
            exc,
            traceback_text=traceback.format_exc(),
        )
        await _update_persisted_job_run(run_id, run_state)
        raise

    run_state = mark_job_complete(job_id, name, trigger, result)
    await _update_persisted_job_run(run_id, run_state)
    return result


async def _invoke_runner(runner: Callable[[], Awaitable[object]], trigger: str):
    parameters = inspect.signature(runner).parameters
    if "trigger" in parameters:
        return await runner(trigger=trigger)
    return await runner()


async def _create_persisted_job_run(job_id: str, name: str, trigger: str, run_state) -> str | None:
    try:
        run_id = await create_job_run_record(
            job_id,
            name,
            trigger,
            status=run_state.status,
            started_at=run_state.started_at,
            summary=run_state.summary,
        )
        return str(run_id)
    except Exception as exc:
        logger.warning("job_run_create_failed", job_id=job_id, error=str(exc))
        return None


async def _update_persisted_job_run(run_id: str | None, run_state) -> None:
    if run_id is None:
        return
    try:
        await update_job_run_record(
            uuid.UUID(run_id),
            status=run_state.status,
            completed_at=run_state.completed_at,
            summary=run_state.summary,
            error=run_state.error,
            traceback=run_state.traceback,
            details=run_state.details,
        )
    except Exception as exc:
        logger.warning("job_run_update_failed", run_id=run_id, error=str(exc))

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import Settings
from src.jobs.calendar_sync_job import run_google_calendar_sync
from src.jobs.cleanup_job import cleanup_old_events
from src.jobs.digest_job import run_digest
from src.jobs.ingest_job import run_ingestion

logger = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def create_scheduler(start: bool = True) -> AsyncIOScheduler:
    global _scheduler
    settings = Settings()
    scheduler = AsyncIOScheduler(timezone="America/Chicago")

    scheduler.add_job(
        run_ingestion,
        CronTrigger(hour=6, timezone="America/Chicago"),
        id="ingest_all_sources",
        name="Ingest all sources",
        replace_existing=True,
    )

    scheduler.add_job(
        run_digest,
        CronTrigger(day_of_week="tue,fri", hour=8, timezone="America/Chicago"),
        id="generate_and_send_digest",
        name="Generate and send digest",
        replace_existing=True,
    )

    scheduler.add_job(
        run_google_calendar_sync,
        CronTrigger(
            hour=settings.google_calendar_sync_hour,
            timezone=settings.google_calendar_timezone,
        ),
        id="sync_google_calendar",
        name="Sync Google Calendar",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_old_events,
        CronTrigger(day_of_week="sun", hour=3, timezone="America/Chicago"),
        id="cleanup_old_events",
        name="Archive old events",
        replace_existing=True,
    )

    _scheduler = scheduler

    if start:
        scheduler.start()
        logger.info("scheduler_started", jobs=[j.id for j in scheduler.get_jobs()])

    return scheduler


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

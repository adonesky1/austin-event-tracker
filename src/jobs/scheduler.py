import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.jobs.cleanup_job import cleanup_old_events
from src.jobs.digest_job import run_digest
from src.jobs.ingest_job import run_ingestion

logger = structlog.get_logger()


def create_scheduler(start: bool = True) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Chicago")

    # Daily ingestion at 6am CT
    scheduler.add_job(
        run_ingestion,
        CronTrigger(hour=6, timezone="America/Chicago"),
        id="ingest_all_sources",
        name="Ingest all sources",
        replace_existing=True,
    )

    # Digest on Tue + Fri at 8am CT
    scheduler.add_job(
        run_digest,
        CronTrigger(day_of_week="tue,fri", hour=8, timezone="America/Chicago"),
        id="generate_and_send_digest",
        name="Generate and send digest",
        replace_existing=True,
    )

    # Cleanup on Sunday at 3am CT
    scheduler.add_job(
        cleanup_old_events,
        CronTrigger(day_of_week="sun", hour=3, timezone="America/Chicago"),
        id="cleanup_old_events",
        name="Archive old events",
        replace_existing=True,
    )

    if start:
        scheduler.start()
        logger.info("scheduler_started", jobs=[j.id for j in scheduler.get_jobs()])

    return scheduler

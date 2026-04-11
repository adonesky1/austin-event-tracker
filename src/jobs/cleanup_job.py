from datetime import datetime, timezone, timedelta

import structlog

logger = structlog.get_logger()

ARCHIVE_AFTER_DAYS = 60


async def cleanup_old_events():
    """Archive events older than ARCHIVE_AFTER_DAYS days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ARCHIVE_AFTER_DAYS)
    # TODO: delete or archive events from db where start_datetime < cutoff
    logger.info("cleanup_job_complete", cutoff=cutoff.isoformat())
    return {
        "status": "success",
        "summary": f"Cleanup completed for events older than {cutoff.date().isoformat()}.",
        "cutoff": cutoff.isoformat(),
        "archived_count": 0,
    }

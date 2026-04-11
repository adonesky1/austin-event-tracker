from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select

from src.config.settings import Settings
from src.jobs.runtime_status import _make_json_safe
from src.models.database import create_engine, create_session_factory
from src.models.job_run import JobRun


async def create_job_run_record(
    job_id: str,
    job_name: str,
    trigger: str,
    *,
    status: str,
    started_at: datetime | None,
    summary: str | None = None,
) -> uuid.UUID:
    settings = Settings()
    engine = create_engine(settings)
    Session = create_session_factory(engine)
    try:
        async with Session() as session:
            row = JobRun(
                job_id=job_id,
                job_name=job_name,
                trigger=trigger,
                status=status,
                started_at=started_at,
                summary=summary,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id
    finally:
        await engine.dispose()


async def update_job_run_record(
    run_id: uuid.UUID,
    *,
    status: str,
    completed_at: datetime | None,
    summary: str | None,
    error: str | None,
    traceback: str | None,
    details: dict[str, Any] | None,
) -> None:
    settings = Settings()
    engine = create_engine(settings)
    Session = create_session_factory(engine)
    try:
        async with Session() as session:
            row = await session.get(JobRun, run_id)
            if row is None:
                return

            row.status = status
            row.completed_at = completed_at
            row.summary = summary
            row.error = error
            row.traceback = traceback
            row.details = _make_json_safe(details) if details is not None else None
            await session.commit()
    finally:
        await engine.dispose()


async def list_recent_job_runs(
    session,
    *,
    limit_per_job: int = 5,
    total_limit: int = 100,
) -> dict[str, list[dict[str, Any]]]:
    rows = (
        (
            await session.execute(
                select(JobRun).order_by(desc(JobRun.created_at)).limit(total_limit)
            )
        )
        .scalars()
        .all()
    )

    runs_by_job: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        bucket = runs_by_job.setdefault(row.job_id, [])
        if len(bucket) >= limit_per_job:
            continue
        bucket.append(serialize_job_run(row))
    return runs_by_job


def serialize_job_run(row: JobRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "job_id": row.job_id,
        "job_name": row.job_name,
        "trigger": row.trigger,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "summary": row.summary,
        "error": row.error,
        "traceback": row.traceback,
        "details": row.details,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

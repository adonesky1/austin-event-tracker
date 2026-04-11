import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.admin.service import (
    create_tracked_item,
    delete_tracked_item,
    get_or_create_profile,
    serialize_profile,
    serialize_prompt_config,
    serialize_tracked_item,
    update_profile,
    update_prompt_config,
    update_tracked_item,
)
from src.api.deps import verify_admin_key
from src.config.settings import Settings
from src.jobs.calendar_sync_job import (
    get_latest_calendar_sync_status,
    preview_google_calendar_sync,
    run_google_calendar_sync,
)
from src.llm.prompt_loader import get_effective_synthesis_prompts
from src.models.database import create_engine, create_session_factory
from src.schemas.admin import (
    PromptConfigResponse,
    PromptConfigUpdate,
    TrackedItemCreate,
    TrackedItemResponse,
    TrackedItemUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_admin_key)])


class SourceToggleResponse(BaseModel):
    source: str
    enabled: bool
    message: str


class CalendarSyncResponse(BaseModel):
    status: str
    trigger: str
    dry_run: bool
    window_start: str
    window_end: str
    selected_count: int
    created_count: int
    updated_count: int
    deleted_count: int
    selected_events: list[dict]
    error: str | None = None


class JobRuntimeInfo(BaseModel):
    status: str = "idle"
    trigger: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    details: dict | None = None


class JobRunInfo(BaseModel):
    id: str
    job_id: str
    job_name: str
    trigger: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    summary: Optional[str]
    error: Optional[str]
    traceback: Optional[str]
    details: dict | None = None
    created_at: Optional[str]


class JobInfo(BaseModel):
    id: str
    name: str
    day_of_week: Optional[str]
    hour: int
    next_run: Optional[str]
    enabled: bool
    runtime: JobRuntimeInfo = Field(default_factory=JobRuntimeInfo)
    recent_runs: list[JobRunInfo] = Field(default_factory=list)


class JobScheduleUpdate(BaseModel):
    day_of_week: Optional[str] = None
    hour: int


class DigestSummary(BaseModel):
    id: str
    subject: str
    sent_at: Optional[str]
    status: str
    event_count: int
    window_start: str
    window_end: str


class DigestDetail(DigestSummary):
    html_content: str
    plaintext_content: str


@router.get("/profile", response_model=UserProfileResponse)
async def admin_profile():
    return await _with_session(_load_profile)


@router.patch("/profile", response_model=UserProfileResponse)
async def admin_profile_update(payload: UserProfileUpdate):
    return await _with_session(lambda session, settings: _update_profile(session, settings, payload))


@router.get("/prompts/synthesis", response_model=PromptConfigResponse)
async def admin_prompt_synthesis():
    return await _with_session(_load_synthesis_prompt)


@router.put("/prompts/synthesis", response_model=PromptConfigResponse)
async def admin_prompt_synthesis_update(payload: PromptConfigUpdate):
    return await _with_session(
        lambda session, settings: _update_synthesis_prompt(session, settings, payload)
    )


@router.post("/prompts/synthesis/reset", response_model=PromptConfigResponse)
async def admin_prompt_synthesis_reset():
    return await _with_session(_reset_synthesis_prompt)


@router.get("/tracked-items", response_model=list[TrackedItemResponse])
async def admin_tracked_items():
    return await _with_session(_list_tracked_items)


@router.post("/tracked-items", response_model=TrackedItemResponse)
async def admin_tracked_items_create(payload: TrackedItemCreate):
    return await _with_session(lambda session, settings: _create_tracked_item(session, payload))


@router.patch("/tracked-items/{item_id}", response_model=TrackedItemResponse)
async def admin_tracked_items_update(item_id: uuid.UUID, payload: TrackedItemUpdate):
    return await _with_session(
        lambda session, settings: _update_tracked_item(session, item_id, payload)
    )


@router.delete("/tracked-items/{item_id}")
async def admin_tracked_items_delete(item_id: uuid.UUID):
    return await _with_session(lambda session, settings: _delete_tracked_item(session, item_id))


@router.get("/sources")
async def list_sources():
    """List all sources and their health status."""
    # TODO: query source_health table from db
    return {
        "sources": [
            {"name": "eventbrite", "type": "api", "status": "healthy", "enabled": True},
            {"name": "bandsintown", "type": "api", "status": "healthy", "enabled": True},
            {"name": "do512", "type": "scraper", "status": "healthy", "enabled": True},
            {"name": "austin_chronicle", "type": "scraper", "status": "healthy", "enabled": True},
            {"name": "instagram", "type": "scraper", "status": "disabled", "enabled": False},
        ]
    }


@router.post("/sources/{name}/toggle")
async def toggle_source(name: str) -> SourceToggleResponse:
    """Enable or disable a source."""
    # TODO: update source enabled state in db or config
    return SourceToggleResponse(
        source=name,
        enabled=True,
        message=f"Source {name} toggled (TODO: persist to db)",
    )


@router.post("/ingest")
async def trigger_ingest():
    """Trigger ingestion for all enabled sources now."""
    from src.jobs.scheduler import trigger_job_now

    try:
        trigger_job_now("ingest_all_sources")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "queued", "message": "Ingestion job queued"}


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

@router.get("/jobs", response_model=list[JobInfo])
async def list_jobs():
    from src.jobs.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    recent_runs_by_job = {}
    try:
        recent_runs_by_job = await _with_session(_load_recent_job_runs_by_job)
    except Exception:
        recent_runs_by_job = {}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(_serialize_job_info(job, recent_runs_by_job.get(job.id, [])))
    return jobs


@router.post("/jobs/{job_id}/trigger", response_model=JobInfo)
async def trigger_job(job_id: str):
    from src.jobs.scheduler import get_scheduler, trigger_job_now
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    job = scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    try:
        trigger_job_now(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    job = scheduler.get_job(job_id)
    recent_runs_by_job = {}
    try:
        recent_runs_by_job = await _with_session(_load_recent_job_runs_by_job)
    except Exception:
        recent_runs_by_job = {}
    return _serialize_job_info(job, recent_runs_by_job.get(job_id, []))


@router.put("/jobs/{job_id}/schedule", response_model=JobInfo)
async def update_job_schedule(job_id: str, payload: JobScheduleUpdate):
    from src.jobs.scheduler import get_scheduler, reschedule_job
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    job = scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    await reschedule_job(job_id, payload.day_of_week, payload.hour)
    job = scheduler.get_job(job_id)
    recent_runs_by_job = {}
    try:
        recent_runs_by_job = await _with_session(_load_recent_job_runs_by_job)
    except Exception:
        recent_runs_by_job = {}
    return _serialize_job_info(job, recent_runs_by_job.get(job_id, []))


# ---------------------------------------------------------------------------
# Digest history
# ---------------------------------------------------------------------------

@router.get("/digests", response_model=dict)
async def list_digests(limit: int = 20, offset: int = 0):
    return await _with_session(lambda session, settings: _list_digests(session, limit, offset))


@router.get("/digests/{digest_id}", response_model=DigestDetail)
async def get_digest(digest_id: uuid.UUID):
    result = await _with_session(lambda session, settings: _get_digest(session, digest_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return result


@router.post("/digest/send")
async def send_digest():
    """Generate and send the next digest."""
    from src.jobs.scheduler import trigger_job_now

    try:
        trigger_job_now("generate_and_send_digest")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "queued", "message": "Digest job queued"}


@router.get("/calendar/status")
async def calendar_status():
    return await get_latest_calendar_sync_status()


@router.get("/calendar/preview", response_model=CalendarSyncResponse)
async def calendar_preview():
    try:
        preview = await preview_google_calendar_sync()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _serialize_calendar_response(preview)


@router.post("/calendar/sync", response_model=CalendarSyncResponse)
async def calendar_sync():
    result = await run_google_calendar_sync(trigger="manual")
    if result.get("status") == "skipped":
        raise HTTPException(status_code=400, detail=result.get("reason", "Sync skipped"))
    return _serialize_calendar_response(result)


@router.get("/events")
async def list_events(
    category: str | None = None,
    city: str = "austin",
    limit: int = 50,
    offset: int = 0,
):
    """Browse stored events with optional filters."""
    # TODO: query events from db
    return {
        "events": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "filters": {"category": category, "city": city},
    }


async def _with_session(callback):
    settings = Settings()
    engine = create_engine(settings)
    Session = create_session_factory(engine)
    try:
        async with Session() as session:
            return await callback(session, settings)
    finally:
        await engine.dispose()


async def _load_profile(session, settings):
    profile = await get_or_create_profile(session, settings)
    return serialize_profile(profile)


def _serialize_job_info(job, recent_runs: list[dict] | None = None) -> JobInfo:
    day_of_week, hour = _extract_job_schedule(job)
    next_run = job.next_run_time.isoformat() if job.next_run_time else None
    from src.jobs.runtime_status import get_job_runtime_snapshot

    recent_runs = recent_runs or []
    runtime = _resolve_job_runtime(
        get_job_runtime_snapshot(job.id, job.name),
        recent_runs,
    )
    return JobInfo(
        id=job.id,
        name=job.name,
        day_of_week=day_of_week,
        hour=hour,
        next_run=next_run,
        enabled=True,
        runtime=JobRuntimeInfo(**runtime),
        recent_runs=[JobRunInfo(**run) for run in recent_runs],
    )


def _extract_job_schedule(job) -> tuple[str | None, int]:
    trigger = job.trigger
    day_of_week = None
    hour = 0
    if hasattr(trigger, "fields"):
        for field in trigger.fields:
            if field.name == "day_of_week" and not field.is_default:
                day_of_week = str(field)
            if field.name == "hour" and not field.is_default:
                hour = int(str(field))
    return day_of_week, hour


def _resolve_job_runtime(runtime: dict, recent_runs: list[dict]) -> dict:
    has_live_state = any(
        runtime.get(key)
        for key in ("summary", "error", "started_at", "completed_at", "trigger")
    ) or runtime.get("status") != "idle"
    if has_live_state or not recent_runs:
        return runtime

    latest = recent_runs[0]
    return {
        "status": latest.get("status", "idle"),
        "trigger": latest.get("trigger"),
        "started_at": latest.get("started_at"),
        "completed_at": latest.get("completed_at"),
        "summary": latest.get("summary"),
        "error": latest.get("error"),
        "traceback": latest.get("traceback"),
        "details": latest.get("details"),
    }


async def _load_recent_job_runs_by_job(session, settings):
    from src.jobs.job_run_store import list_recent_job_runs

    return await list_recent_job_runs(session)


async def _update_profile(session, settings, payload: UserProfileUpdate):
    profile = await update_profile(session, settings, payload)
    return serialize_profile(profile)


async def _load_synthesis_prompt(session, settings):
    system_prompt, user_prompt_template = await get_effective_synthesis_prompts(session)
    prompt = await _get_prompt_record(session)
    return serialize_prompt_config(
        prompt,
        key="synthesis",
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
    )


async def _update_synthesis_prompt(session, settings, payload: PromptConfigUpdate):
    prompt = await update_prompt_config(
        session,
        "synthesis",
        payload.system_prompt,
        payload.user_prompt_template,
    )
    return serialize_prompt_config(
        prompt,
        key="synthesis",
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
    )


async def _reset_synthesis_prompt(session, settings):
    from src.admin.service import get_prompt_config, reset_prompt_config

    await reset_prompt_config(session, "synthesis")
    system_prompt, user_prompt_template = await get_effective_synthesis_prompts(session)
    prompt = await get_prompt_config(session, "synthesis")
    return serialize_prompt_config(
        prompt,
        key="synthesis",
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
    )


async def _list_tracked_items(session, settings):
    from src.admin.service import list_tracked_items

    items = await list_tracked_items(session)
    return [serialize_tracked_item(item) for item in items]


async def _create_tracked_item(session, payload: TrackedItemCreate):
    item = await create_tracked_item(session, payload)
    return serialize_tracked_item(item)


async def _update_tracked_item(session, item_id: uuid.UUID, payload: TrackedItemUpdate):
    item = await update_tracked_item(session, item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Tracked item not found")
    return serialize_tracked_item(item)


async def _delete_tracked_item(session, item_id: uuid.UUID):
    deleted = await delete_tracked_item(session, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tracked item not found")
    return {"status": "deleted"}


async def _get_prompt_record(session):
    from src.admin.service import get_prompt_config

    return await get_prompt_config(session, "synthesis")


async def _list_digests(session, limit: int, offset: int):
    from sqlalchemy import select, func
    from src.models.digest import Digest

    total_result = await session.execute(select(func.count()).select_from(Digest))
    total = total_result.scalar()

    rows = (
        await session.execute(
            select(Digest).order_by(Digest.sent_at.desc().nullslast()).limit(limit).offset(offset)
        )
    ).scalars().all()

    digests = [
        {
            "id": str(d.id),
            "subject": d.subject,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "status": d.status.value,
            "event_count": len(d.event_ids) if d.event_ids else 0,
            "window_start": d.window_start.isoformat(),
            "window_end": d.window_end.isoformat(),
        }
        for d in rows
    ]
    return {"digests": digests, "total": total}


async def _get_digest(session, digest_id: uuid.UUID):
    from sqlalchemy import select
    from src.models.digest import Digest

    row = (
        await session.execute(select(Digest).where(Digest.id == digest_id))
    ).scalar_one_or_none()

    if row is None:
        return None

    return {
        "id": str(row.id),
        "subject": row.subject,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "status": row.status.value,
        "event_count": len(row.event_ids) if row.event_ids else 0,
        "window_start": row.window_start.isoformat(),
        "window_end": row.window_end.isoformat(),
        "html_content": row.html_content,
        "plaintext_content": row.plaintext_content,
    }


def _serialize_calendar_response(payload: dict) -> dict:
    return {
        "status": payload["status"],
        "trigger": payload["trigger"],
        "dry_run": payload["dry_run"],
        "window_start": payload["window_start"].isoformat()
        if hasattr(payload["window_start"], "isoformat")
        else payload["window_start"],
        "window_end": payload["window_end"].isoformat()
        if hasattr(payload["window_end"], "isoformat")
        else payload["window_end"],
        "selected_count": payload["selected_count"],
        "created_count": payload["created_count"],
        "updated_count": payload["updated_count"],
        "deleted_count": payload["deleted_count"],
        "selected_events": payload.get("selected_events", []),
        "error": payload.get("error"),
    }

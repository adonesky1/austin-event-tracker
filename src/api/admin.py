import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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
    # TODO: call ingestion pipeline directly or enqueue job
    return {"status": "triggered", "message": "Ingestion job started"}


@router.post("/digest/preview")
async def preview_digest():
    """Generate a digest without sending it."""
    # TODO: run ranking + generation pipeline, return preview
    return {"status": "ok", "message": "Preview generated (TODO: return HTML)"}


@router.post("/digest/send")
async def send_digest():
    """Generate and send the next digest."""
    # TODO: run full digest pipeline and send
    return {"status": "ok", "message": "Digest sent (TODO: run pipeline)"}


@router.post("/digest/{digest_id}/resend")
async def resend_digest(digest_id: str):
    """Resend a previously generated digest."""
    # TODO: load digest from db and resend
    return {"status": "ok", "message": f"Digest {digest_id} resent (TODO)"}


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

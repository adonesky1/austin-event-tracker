from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import verify_admin_key
from src.jobs.calendar_sync_job import (
    get_latest_calendar_sync_status,
    preview_google_calendar_sync,
    run_google_calendar_sync,
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

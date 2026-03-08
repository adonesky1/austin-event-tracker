from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import verify_admin_key

router = APIRouter(prefix="/admin", dependencies=[Depends(verify_admin_key)])


class SourceToggleResponse(BaseModel):
    source: str
    enabled: bool
    message: str


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

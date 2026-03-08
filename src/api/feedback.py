import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.api.deps import get_settings
from src.config.settings import Settings
from src.digest.generator import DigestGenerator

logger = structlog.get_logger()

router = APIRouter(prefix="/api/feedback")

VALID_FEEDBACK_TYPES = {
    "thumbs_up", "thumbs_down", "more_like_this", "less_like_this",
    "too_far", "too_expensive", "wrong_age", "already_knew",
}

FEEDBACK_MESSAGES = {
    "thumbs_up": "Thanks! We'll show you more events like this.",
    "thumbs_down": "Noted. We'll show you fewer events like this.",
    "more_like_this": "Great! We'll prioritize similar events.",
    "less_like_this": "Got it. We'll dial back on this type.",
    "too_far": "Understood. We'll focus on closer events.",
    "too_expensive": "Noted. We'll emphasize more budget-friendly picks.",
    "wrong_age": "Thanks for the feedback on age suitability.",
    "already_knew": "Appreciated! We'll try to surface fresher finds.",
}


@router.get("/{event_id}", response_class=HTMLResponse)
async def record_feedback(
    event_id: str,
    type: str = Query(..., description="Feedback type"),
    token: str = Query(..., description="Signed verification token"),
    settings: Settings = Depends(get_settings),
):
    if type not in VALID_FEEDBACK_TYPES:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    generator = DigestGenerator(
        base_url=settings.base_url,
        feedback_secret=settings.feedback_secret,
    )

    if not generator.verify_feedback_token(event_id, token):
        raise HTTPException(status_code=403, detail="Invalid or expired feedback token")

    # TODO: persist feedback to database when db session is wired in
    logger.info("feedback_received", event_id=event_id, type=type)

    message = FEEDBACK_MESSAGES.get(type, "Feedback received.")
    return HTMLResponse(content=_thanks_page(message), status_code=200)


def _thanks_page(message: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Feedback</title>
<style>body{{font-family:system-ui;max-width:400px;margin:80px auto;text-align:center;color:#444;}}</style>
</head><body>
<h2>Thanks! 🎉</h2>
<p>{message}</p>
<p><small>You can close this tab.</small></p>
</body></html>"""

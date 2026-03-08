import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from itsdangerous import URLSafeSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.digest.sections import group_events_into_sections
from src.schemas.event import NormalizedEvent

logger = structlog.get_logger()

SECTION_LABELS = {
    "top_picks": "Top Picks",
    "kids_family": "Kids & Family",
    "date_night": "Date Night",
    "this_weekend": "This Weekend",
    "plan_ahead": "Worth Planning Ahead",
    "free_cheap": "Free & Cheap",
}

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"


class DigestGenerator:
    def __init__(self, base_url: str, feedback_secret: str):
        self.base_url = base_url
        self.serializer = URLSafeSerializer(feedback_secret, salt="feedback")
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self.env.filters["format_datetime"] = _format_datetime

    def render_html(
        self,
        events_with_scores: list[tuple[NormalizedEvent, float]],
        window_start: str,
        window_end: str,
        digest_id: str | None = None,
    ) -> str:
        sections = group_events_into_sections(events_with_scores)
        feedback_tokens = self._build_feedback_tokens(events_with_scores)
        template = self.env.get_template("digest.html")
        return template.render(
            sections=sections,
            section_labels=SECTION_LABELS,
            window_start=window_start,
            window_end=window_end,
            base_url=self.base_url,
            digest_id=digest_id or str(uuid.uuid4()),
            feedback_tokens=feedback_tokens,
            subject=f"Austin Family Events: {window_start} – {window_end}",
        )

    def render_plaintext(
        self,
        events_with_scores: list[tuple[NormalizedEvent, float]],
        window_start: str,
        window_end: str,
        digest_id: str | None = None,
    ) -> str:
        sections = group_events_into_sections(events_with_scores)
        feedback_tokens = self._build_feedback_tokens(events_with_scores)
        template = self.env.get_template("digest.txt")
        return template.render(
            sections=sections,
            section_labels=SECTION_LABELS,
            window_start=window_start,
            window_end=window_end,
            base_url=self.base_url,
            digest_id=digest_id or str(uuid.uuid4()),
            feedback_tokens=feedback_tokens,
        )

    def generate_subject(self, window_start: str, window_end: str) -> str:
        return f"Austin Family Events: {window_start} – {window_end}"

    def _build_feedback_tokens(
        self, events_with_scores: list[tuple[NormalizedEvent, float]]
    ) -> dict[str, str]:
        tokens = {}
        for event, _ in events_with_scores:
            token = self.serializer.dumps(str(event.id))
            tokens[str(event.id)] = token
        return tokens

    def verify_feedback_token(self, event_id: str, token: str) -> bool:
        try:
            return self.serializer.loads(token) == event_id
        except Exception:
            return False


def _format_datetime(dt: datetime) -> str:
    try:
        return dt.strftime("%a %b %-d, %-I:%M %p")
    except ValueError:
        return dt.strftime("%a %b %d, %I:%M %p")

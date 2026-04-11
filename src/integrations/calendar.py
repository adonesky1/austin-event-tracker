import asyncio
import base64
import hashlib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

import structlog

from src.config.settings import Settings
from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema

logger = structlog.get_logger()

APP_MANAGED_PUBLISHER = "austin-event-tracker"
FALLBACK_LINK_LABEL = "Source unavailable"


class GoogleCalendarAuthError(RuntimeError):
    """Raised when Google Calendar OAuth credentials need to be refreshed."""


class CalendarIntegration(ABC):
    """Interface for calendar integrations (Google Calendar, Apple Calendar, etc.)."""

    @abstractmethod
    async def authenticate(self, credentials: dict | None = None) -> bool: ...

    @abstractmethod
    async def create_event(self, event_data: dict) -> str: ...

    @abstractmethod
    async def update_event(self, event_id: str, event_data: dict) -> bool: ...

    @abstractmethod
    async def delete_event(self, event_id: str) -> bool: ...

    @abstractmethod
    async def check_duplicate(self, event_data: dict) -> str | None: ...


@dataclass
class CalendarSyncResult:
    status: str
    trigger: str
    dry_run: bool
    window_start: date
    window_end: date
    selected_count: int
    created_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    selected_events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GoogleCalendarIntegration(CalendarIntegration):
    """Google Calendar integration backed by the Calendar API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._service = None

    async def authenticate(self, credentials: dict | None = None) -> bool:
        del credentials
        try:
            service = self._create_service()
            request = service.calendars().get(calendarId=self.settings.google_calendar_id)
            await self._execute(request)
            return True
        except Exception as exc:  # pragma: no cover - exercised through higher-level tests
            logger.error("google_calendar_authenticate_failed", error=str(exc))
            return False

    async def create_event(self, event_data: dict) -> str:
        request = self._create_service().events().insert(
            calendarId=self.settings.google_calendar_id,
            body=event_data,
        )
        created = await self._execute(request)
        return created["id"]

    async def update_event(self, event_id: str, event_data: dict) -> bool:
        request = self._create_service().events().update(
            calendarId=self.settings.google_calendar_id,
            eventId=event_id,
            body=event_data,
        )
        await self._execute(request)
        return True

    async def delete_event(self, event_id: str) -> bool:
        request = self._create_service().events().delete(
            calendarId=self.settings.google_calendar_id,
            eventId=event_id,
        )
        await self._execute(request)
        return True

    async def check_duplicate(self, event_data: dict) -> str | None:
        event_id = event_data.get("id")
        if not event_id:
            return None

        try:
            request = self._create_service().events().get(
                calendarId=self.settings.google_calendar_id,
                eventId=event_id,
            )
            event = await self._execute(request)
            return event.get("id")
        except Exception:
            return None

    async def preview_sync(
        self,
        events_with_scores: list[tuple[NormalizedEvent, float]],
        profile: UserProfileSchema,
        trigger: str = "manual_preview",
    ) -> CalendarSyncResult:
        return await self._reconcile(events_with_scores, profile, dry_run=True, trigger=trigger)

    async def sync_events(
        self,
        events_with_scores: list[tuple[NormalizedEvent, float]],
        profile: UserProfileSchema,
        trigger: str = "scheduler",
    ) -> CalendarSyncResult:
        return await self._reconcile(events_with_scores, profile, dry_run=False, trigger=trigger)

    async def _reconcile(
        self,
        events_with_scores: list[tuple[NormalizedEvent, float]],
        profile: UserProfileSchema,
        dry_run: bool,
        trigger: str,
    ) -> CalendarSyncResult:
        now = datetime.now(timezone.utc)
        window_end = (now + timedelta(days=self.settings.google_calendar_horizon_days)).date()
        desired = {
            payload["id"]: payload
            for payload in [
                build_google_event_payload(
                    event=event,
                    score=score,
                    profile=profile,
                    settings=self.settings,
                )
                for event, score in events_with_scores
            ]
        }

        existing_items = await self.list_managed_events(now=now)
        existing = {item["id"]: item for item in existing_items}

        to_create = sorted(set(desired) - set(existing))
        to_delete = sorted(set(existing) - set(desired))
        to_update = sorted(
            event_id
            for event_id in (set(desired) & set(existing))
            if _existing_payload_hash(existing[event_id]) != _desired_payload_hash(desired[event_id])
        )

        result = CalendarSyncResult(
            status="success",
            trigger=trigger,
            dry_run=dry_run,
            window_start=now.date(),
            window_end=window_end,
            selected_count=len(desired),
            created_count=len(to_create),
            updated_count=len(to_update),
            deleted_count=len(to_delete),
            selected_events=[
                {
                    "id": payload["id"],
                    "title": payload["summary"],
                    "score": float(
                        payload["extendedProperties"]["private"].get("score", "0.0")
                    ),
                    "start": payload["start"]["dateTime"],
                }
                for payload in desired.values()
            ],
        )

        if dry_run:
            return result

        for event_id in to_create:
            await self.create_event(desired[event_id])
        for event_id in to_update:
            await self.update_event(event_id, desired[event_id])
        for event_id in to_delete:
            await self.delete_event(event_id)

        return result

    async def list_managed_events(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        request = self._create_service().events().list(
            calendarId=self.settings.google_calendar_id,
            timeMin=(now - timedelta(days=1)).isoformat(),
            timeMax=(now + timedelta(days=max(self.settings.google_calendar_horizon_days * 4, 90))).isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        response = await self._execute(request)
        items = response.get("items", [])
        return [item for item in items if _is_managed_event(item)]

    def _create_service(self):
        if self._service is None:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None,
                refresh_token=self.settings.google_calendar_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.settings.google_calendar_client_id,
                client_secret=self.settings.google_calendar_client_secret,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        return self._service

    async def _execute(self, request):
        try:
            return await asyncio.to_thread(request.execute)
        except Exception as exc:
            _raise_google_calendar_auth_error(exc)
            raise


def build_publication_key(event: NormalizedEvent) -> str:
    if event.canonical_event_url:
        return event.canonical_event_url.strip().lower()

    venue = _normalize_key_part(event.venue_name)
    city = _normalize_key_part(event.city)
    title = _normalize_key_part(event.title)
    start = event.start_datetime.astimezone(timezone.utc).isoformat()
    return "|".join([title, start, venue, city])


def build_google_event_id(publication_key: str) -> str:
    digest = hashlib.sha256(publication_key.encode("utf-8")).digest()
    encoded = base64.b32hexencode(digest).decode("ascii").lower().rstrip("=")
    return f"aet{encoded[:40]}"


def build_google_maps_link(event: NormalizedEvent) -> str | None:
    query = ", ".join(
        part for part in [event.venue_name, event.address, event.city] if part
    ).strip()
    if not query:
        return None
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def build_calendar_description(
    event: NormalizedEvent,
    score: float,
    profile: UserProfileSchema,
    settings: Settings | None = None,
) -> str:
    what = _tighten_text(event.editorial_summary or _build_fallback_what(event), 220)
    why = _tighten_text(
        event.relevance_explanation or _build_fallback_why(event, score, profile),
        160,
    )

    links = []
    if event.canonical_event_url:
        links.append(f"Event: {event.canonical_event_url}")
    elif event.source_url:
        links.append(f"Event: {event.source_url}")

    map_link = build_google_maps_link(event)
    if map_link:
        links.append(f"Map: {map_link}")

    if not links:
        links.append(FALLBACK_LINK_LABEL)

    lines = [
        f"What: {what}",
        "",
        f"Why it fits: {why}",
        "",
        "Links:",
        *links,
    ]

    if event.end_datetime is None:
        minutes = settings.google_calendar_fallback_duration_minutes if settings else 120
        lines.extend(
            [
                "",
                f"Note: Source did not provide an end time. Calendar uses a {minutes}-minute placeholder.",
            ]
        )

    return "\n".join(lines)


def build_google_event_payload(
    event: NormalizedEvent,
    score: float,
    profile: UserProfileSchema,
    settings: Settings,
) -> dict[str, Any]:
    publication_key = build_publication_key(event)
    event_id = build_google_event_id(publication_key)
    description = build_calendar_description(event, score, profile, settings=settings)
    end_datetime = event.end_datetime or (
        event.start_datetime
        + timedelta(minutes=settings.google_calendar_fallback_duration_minutes)
    )
    source_url = event.canonical_event_url or event.source_url or ""
    location = ", ".join(part for part in [event.venue_name, event.address] if part).strip() or None

    payload = {
        "id": event_id,
        "summary": event.title,
        "description": description,
        "start": {
            "dateTime": event.start_datetime.isoformat(),
            "timeZone": event.timezone or settings.google_calendar_timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": event.timezone or settings.google_calendar_timezone,
        },
        "endTimeUnspecified": event.end_datetime is None,
        "extendedProperties": {
            "private": {
                "publisher": APP_MANAGED_PUBLISHER,
                "publication_key": publication_key,
                "score": f"{score:.4f}",
                "source_url": source_url,
            }
        },
    }

    if location:
        payload["location"] = location
    if source_url:
        payload["source"] = {
            "title": event.source_name or "Austin Event Tracker",
            "url": source_url,
        }

    payload["extendedProperties"]["private"]["payload_hash"] = _desired_payload_hash(payload)
    return payload


def _desired_payload_hash(payload: dict[str, Any]) -> str:
    relevant = {
        "summary": payload.get("summary"),
        "description": payload.get("description"),
        "location": payload.get("location"),
        "start": payload.get("start"),
        "end": payload.get("end"),
        "endTimeUnspecified": payload.get("endTimeUnspecified"),
        "source": payload.get("source"),
    }
    raw = repr(relevant).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _existing_payload_hash(event: dict[str, Any]) -> str:
    private = ((event.get("extendedProperties") or {}).get("private") or {})
    existing = private.get("payload_hash")
    if existing:
        return existing

    payload = {
        "summary": event.get("summary"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": event.get("start"),
        "end": event.get("end"),
        "endTimeUnspecified": event.get("endTimeUnspecified"),
        "source": event.get("source"),
    }
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _is_managed_event(event: dict[str, Any]) -> bool:
    private = ((event.get("extendedProperties") or {}).get("private") or {})
    return private.get("publisher") == APP_MANAGED_PUBLISHER


def _raise_google_calendar_auth_error(exc: Exception) -> None:
    if not _is_google_refresh_error(exc):
        return

    message = str(exc)
    if "invalid_grant" in message.lower():
        raise GoogleCalendarAuthError(
            "Google Calendar refresh token was rejected (invalid_grant). "
            "Re-run scripts/google_calendar_bootstrap.py, update "
            "GOOGLE_CALENDAR_REFRESH_TOKEN, and restart or redeploy the app. "
            "If the OAuth consent screen is still in Testing mode, Google "
            "refresh tokens can expire after 7 days."
        ) from exc

    raise GoogleCalendarAuthError(f"Google Calendar authentication failed: {message}") from exc


def _is_google_refresh_error(exc: Exception) -> bool:
    if exc.__class__.__name__ == "RefreshError":
        return True

    try:
        from google.auth.exceptions import RefreshError
    except Exception:
        return False

    return isinstance(exc, RefreshError)


def _normalize_key_part(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _tighten_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:!?")
    return f"{truncated}…"


def _build_fallback_what(event: NormalizedEvent) -> str:
    if event.venue_name:
        return f"{event.title} at {event.venue_name}."
    if event.neighborhood:
        return f"{event.title} in {event.neighborhood}."
    return f"{event.title} in {event.city.title()}."


def _build_fallback_why(
    event: NormalizedEvent,
    score: float,
    profile: UserProfileSchema,
) -> str:
    interests = set((profile.interests or []))
    matching_tags = [tag for tag in event.tags if tag in interests]
    if event.category == "kids":
        return "A strong fit for a family outing because it leans kid-friendly."
    if matching_tags:
        top = ", ".join(matching_tags[:2])
        return f"Could be a good match if your family enjoys {top} outings."
    if score >= 0.8 or (event.family_score or 0) >= 0.8:
        return "Looks like a strong family-friendly pick based on the event details."
    return "Worth a look if you want something local and different this week."

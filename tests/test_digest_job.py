import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.schemas.event import NormalizedEvent
from src.schemas.user import UserProfileSchema


def make_event(**overrides):
    base = {
        "title": "Spring Family Fest",
        "category": "kids",
        "start_datetime": datetime(2026, 4, 12, 16, 0, tzinfo=timezone.utc),
        "city": "austin",
    }
    base.update(overrides)
    return NormalizedEvent(**base)


@pytest.mark.asyncio
async def test_run_digest_persists_profile_and_event_ids(monkeypatch):
    from src.jobs import digest_job

    profile_id = uuid.uuid4()
    event = make_event()
    render_digest_ids: list[str | None] = []

    class FakeResult:
        def __init__(self):
            self.profile = UserProfileSchema(
                id=profile_id,
                email="test@example.com",
                interests=["kids"],
            )
            self.generated_at = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)

        def select_digest_candidates(self, **kwargs):
            return [(event, 0.91)]

    class FakeCurationService:
        def __init__(self, settings):
            self.settings = settings

        async def curate(self):
            return FakeResult()

    class FakeGenerator:
        def __init__(self, base_url: str, feedback_secret: str):
            self.base_url = base_url
            self.feedback_secret = feedback_secret

        def render_html(self, events, window_start, window_end, digest_id=None):
            render_digest_ids.append(digest_id)
            return "<html>ok</html>"

        def render_plaintext(self, events, window_start, window_end, digest_id=None):
            render_digest_ids.append(digest_id)
            return "ok"

        def generate_subject(self, window_start, window_end):
            return "Austin Family Events"

    send_mock = AsyncMock(return_value={"id": "message-123"})
    save_mock = AsyncMock(return_value=True)
    update_mock = AsyncMock()

    class FakeEmailChannel:
        def __init__(self, api_key: str, from_email: str):
            self.api_key = api_key
            self.from_email = from_email

        async def send(self, to: str, subject: str, html: str, text: str):
            return await send_mock(to=to, subject=subject, html=html, text=text)

    settings = SimpleNamespace(
        google_calendar_horizon_days=21,
        base_url="http://localhost:8000",
        feedback_secret="test-secret",
        telegram_bot_token="",
        telegram_chat_id="",
        resend_api_key="resend-key",
        from_email="digest@example.com",
    )

    monkeypatch.setattr(digest_job, "Settings", lambda: settings)
    monkeypatch.setattr(digest_job, "CurationService", FakeCurationService)
    monkeypatch.setattr(digest_job, "DigestGenerator", FakeGenerator)
    monkeypatch.setattr(digest_job, "EmailChannel", FakeEmailChannel)
    monkeypatch.setattr(digest_job, "_save_digest", save_mock)
    monkeypatch.setattr(digest_job, "_update_digest_status", update_mock)

    await digest_job._run_digest()

    save_kwargs = save_mock.await_args.kwargs
    assert save_kwargs["user_id"] == profile_id
    assert save_kwargs["event_ids"] == [event.id]
    assert render_digest_ids == [str(save_kwargs["digest_id"]), str(save_kwargs["digest_id"])]

    update_args = update_mock.await_args.args
    assert update_args[0] is settings
    assert update_args[1] == save_kwargs["digest_id"]
    assert update_args[2] == digest_job.DigestStatus.SENT

    send_kwargs = send_mock.await_args.kwargs
    assert send_kwargs["to"] == "test@example.com"
    assert send_kwargs["subject"] == "Austin Family Events"


@pytest.mark.asyncio
async def test_run_digest_skips_persistence_when_profile_id_missing(monkeypatch):
    from src.jobs import digest_job

    event = make_event()

    class FakeResult:
        def __init__(self):
            self.profile = UserProfileSchema(
                email="test@example.com",
                interests=["kids"],
            )
            self.generated_at = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)

        def select_digest_candidates(self, **kwargs):
            return [(event, 0.91)]

    class FakeCurationService:
        def __init__(self, settings):
            self.settings = settings

        async def curate(self):
            return FakeResult()

    class FakeGenerator:
        def __init__(self, base_url: str, feedback_secret: str):
            self.base_url = base_url
            self.feedback_secret = feedback_secret

        def render_html(self, events, window_start, window_end, digest_id=None):
            return "<html>ok</html>"

        def render_plaintext(self, events, window_start, window_end, digest_id=None):
            return "ok"

        def generate_subject(self, window_start, window_end):
            return "Austin Family Events"

    send_mock = AsyncMock(return_value={"id": "message-123"})
    save_mock = AsyncMock(return_value=True)
    update_mock = AsyncMock()

    class FakeEmailChannel:
        def __init__(self, api_key: str, from_email: str):
            self.api_key = api_key
            self.from_email = from_email

        async def send(self, to: str, subject: str, html: str, text: str):
            return await send_mock(to=to, subject=subject, html=html, text=text)

    settings = SimpleNamespace(
        google_calendar_horizon_days=21,
        base_url="http://localhost:8000",
        feedback_secret="test-secret",
        telegram_bot_token="",
        telegram_chat_id="",
        resend_api_key="resend-key",
        from_email="digest@example.com",
    )

    monkeypatch.setattr(digest_job, "Settings", lambda: settings)
    monkeypatch.setattr(digest_job, "CurationService", FakeCurationService)
    monkeypatch.setattr(digest_job, "DigestGenerator", FakeGenerator)
    monkeypatch.setattr(digest_job, "EmailChannel", FakeEmailChannel)
    monkeypatch.setattr(digest_job, "_save_digest", save_mock)
    monkeypatch.setattr(digest_job, "_update_digest_status", update_mock)

    await digest_job._run_digest()

    assert save_mock.await_count == 0
    assert update_mock.await_count == 0
    assert send_mock.await_count == 1

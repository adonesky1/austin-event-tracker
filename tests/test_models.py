def test_event_model_has_required_columns():
    from src.models.event import Event

    cols = {c.name for c in Event.__table__.columns}
    required = {"id", "title", "start_datetime", "city", "category", "canonical_event_url"}
    assert required.issubset(cols)


def test_event_source_model():
    from src.models.event import EventSource

    cols = {c.name for c in EventSource.__table__.columns}
    assert "raw_payload" in cols
    assert "source_name" in cols


def test_user_profile_model():
    from src.models.user import UserProfile

    cols = {c.name for c in UserProfile.__table__.columns}
    assert "email" in cols
    assert "interests" in cols


def test_digest_model():
    from src.models.digest import Digest

    cols = {c.name for c in Digest.__table__.columns}
    assert "html_content" in cols
    assert "status" in cols


def test_feedback_model():
    from src.models.feedback import Feedback

    cols = {c.name for c in Feedback.__table__.columns}
    assert "feedback_type" in cols


def test_source_health_model():
    from src.models.source_health import SourceHealth

    cols = {c.name for c in SourceHealth.__table__.columns}
    assert "source_name" in cols
    assert "status" in cols


def test_all_models_importable():
    from src.models import (
        Base,
        CalendarSyncRun,
        Digest,
        Event,
        EventSource,
        Feedback,
        PromptConfig,
        SourceHealth,
        TrackedItem,
        UserProfile,
    )

    assert CalendarSyncRun.__tablename__ in Base.metadata.tables
    assert PromptConfig.__tablename__ in Base.metadata.tables
    assert TrackedItem.__tablename__ in Base.metadata.tables
    assert len(Base.metadata.tables) == 9

def test_load_austin_config(austin_config):
    assert austin_config.name == "austin"
    assert austin_config.timezone == "America/Chicago"
    assert "Downtown" in austin_config.neighborhoods
    assert "eventbrite" in austin_config.default_sources


def test_austin_config_coordinates(austin_config):
    assert 30.0 < austin_config.latitude < 31.0
    assert -98.0 < austin_config.longitude < -97.0


def test_austin_config_has_radius(austin_config):
    assert austin_config.radius_miles == 30


def test_google_calendar_defaults():
    from src.config.settings import Settings

    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        anthropic_api_key="test-key",
        resend_api_key="test-key",
    )

    assert settings.google_calendar_enabled is False
    assert settings.google_calendar_min_score == 0.65
    assert settings.google_calendar_horizon_days == 21
    assert settings.google_calendar_fallback_duration_minutes == 120
    assert settings.google_calendar_sync_hour == 7
    assert settings.google_calendar_timezone == "America/Chicago"
    assert settings.google_calendar_calendar_name == "Austin Curated Events"


def test_google_calendar_requires_credentials_only_when_enabled():
    from pydantic import ValidationError

    from src.config.settings import Settings

    try:
        Settings(
            database_url="sqlite+aiosqlite:///test.db",
            anthropic_api_key="test-key",
            resend_api_key="test-key",
            google_calendar_enabled=True,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected missing Google Calendar credentials to fail validation")

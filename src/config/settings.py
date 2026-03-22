from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://events:events@localhost:5432/events"
    anthropic_api_key: str = ""
    resend_api_key: str = ""
    eventbrite_api_key: str = ""
    bandsintown_app_id: str = ""
    admin_api_key: str = "changeme"
    default_city: str = "austin"
    digest_schedule_days: str = "tue,fri"
    digest_hour: int = 8
    from_email: str = "events@localhost"
    base_url: str = "http://localhost:8000"
    feedback_secret: str = "changeme"
    log_level: str = "INFO"
    google_calendar_enabled: bool = False
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""
    google_calendar_refresh_token: str = ""
    google_calendar_id: str = ""
    google_calendar_min_score: float = 0.65
    google_calendar_horizon_days: int = 21
    google_calendar_fallback_duration_minutes: int = 120
    google_calendar_sync_hour: int = 7
    google_calendar_timezone: str = "America/Chicago"
    google_calendar_calendar_name: str = "Austin Curated Events"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_google_calendar_settings(self):
        if not self.google_calendar_enabled:
            return self

        required = {
            "google_calendar_client_id": self.google_calendar_client_id,
            "google_calendar_client_secret": self.google_calendar_client_secret,
            "google_calendar_refresh_token": self.google_calendar_refresh_token,
            "google_calendar_id": self.google_calendar_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(f"Missing required Google Calendar settings: {fields}")

        return self

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

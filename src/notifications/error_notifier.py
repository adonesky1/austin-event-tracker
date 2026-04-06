import httpx
import structlog

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org"


async def notify_job_failure(job_name: str, error: Exception) -> None:
    from src.config.settings import Settings

    settings = Settings()
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        return

    message = f"[Job Failure] {job_name}: {type(error).__name__}: {str(error)[:200]}"
    url = f"{TELEGRAM_API}/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json={"chat_id": settings.telegram_chat_id, "text": message},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("error_notifier_failed", error=str(exc))

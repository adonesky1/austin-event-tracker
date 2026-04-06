import httpx
import structlog

from src.notifications.base import NotificationChannel

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


class TelegramChannel(NotificationChannel):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, to: str, subject: str, html: str, text: str) -> dict:
        # Truncate to Telegram's limit, keeping subject as header
        body = f"*{subject}*\n\n{text}"
        if len(body) > MAX_MESSAGE_LENGTH:
            body = body[: MAX_MESSAGE_LENGTH - 3] + "..."

        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": body,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        logger.info("telegram_send_complete", chat_id=self.chat_id, ok=data.get("ok"))
        return {"id": str(data.get("result", {}).get("message_id", ""))}

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
        body = f"{subject}\n\n{text}"
        # Split into chunks that fit Telegram's limit
        chunks = [
            body[i: i + MAX_MESSAGE_LENGTH]
            for i in range(0, len(body), MAX_MESSAGE_LENGTH)
        ]

        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        last_id = ""
        async with httpx.AsyncClient(timeout=30) as client:
            for chunk in chunks:
                payload = {"chat_id": self.chat_id, "text": chunk}
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                last_id = str(data.get("result", {}).get("message_id", ""))

        logger.info("telegram_send_complete", chat_id=self.chat_id, chunks=len(chunks))
        return {"id": last_id}

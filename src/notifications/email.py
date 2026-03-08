import structlog
import resend

from src.notifications.base import NotificationChannel

logger = structlog.get_logger()


class EmailChannel(NotificationChannel):
    def __init__(self, api_key: str, from_email: str):
        resend.api_key = api_key
        self.from_email = from_email

    async def send(self, to: str, subject: str, html: str, text: str) -> dict:
        try:
            result = resend.Emails.send({
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            })
            logger.info("email_sent", to=to, subject=subject)
            return result
        except Exception as e:
            logger.error("email_send_failed", to=to, error=str(e))
            raise

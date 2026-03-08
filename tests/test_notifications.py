import pytest
from unittest.mock import MagicMock, patch

from src.notifications.base import NotificationChannel, PushChannel


def test_notification_channel_is_abstract():
    with pytest.raises(TypeError):
        NotificationChannel()


def test_push_channel_not_implemented():
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(PushChannel().send("to", "sub", "html", "text"))


@pytest.mark.asyncio
async def test_email_channel_sends():
    from src.notifications.email import EmailChannel

    mock_result = {"id": "email-123"}
    with patch("resend.Emails.send", return_value=mock_result) as mock_send:
        channel = EmailChannel(api_key="test-key", from_email="from@example.com")
        result = await channel.send(
            to="user@example.com",
            subject="Your Austin Events",
            html="<h1>Events</h1>",
            text="Events",
        )

    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["user@example.com"]
    assert call_args["subject"] == "Your Austin Events"
    assert result == {"id": "email-123"}


@pytest.mark.asyncio
async def test_email_channel_raises_on_failure():
    from src.notifications.email import EmailChannel

    with patch("resend.Emails.send", side_effect=Exception("API error")):
        channel = EmailChannel(api_key="test-key", from_email="from@example.com")
        with pytest.raises(Exception, match="API error"):
            await channel.send("to", "sub", "html", "text")

from abc import ABC, abstractmethod


class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, html: str, text: str) -> dict: ...


class PushChannel(NotificationChannel):
    """TODO: Implement push notifications.

    Interface ready for: FCM, APNs, or web push.
    Needs:
    - Device token registration endpoint
    - Quiet hours config (e.g. no push after 9pm)
    - Urgency levels (standout event vs regular digest)
    - Opt-in management per user
    """

    async def send(self, to: str, subject: str, html: str, text: str) -> dict:
        raise NotImplementedError("Push notifications not yet implemented")

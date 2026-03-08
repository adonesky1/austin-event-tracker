from abc import ABC, abstractmethod


class CalendarIntegration(ABC):
    """Interface for calendar integrations (Google Calendar, Apple Calendar, etc.)"""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> bool: ...

    @abstractmethod
    async def create_event(self, event_data: dict) -> str: ...

    @abstractmethod
    async def update_event(self, event_id: str, event_data: dict) -> bool: ...

    @abstractmethod
    async def check_duplicate(self, event_data: dict) -> str | None: ...


class GoogleCalendarIntegration(CalendarIntegration):
    """TODO: Implement Google Calendar integration.

    Needs:
    - OAuth 2.0 flow for user authorization
    - Google Calendar API v3 client
    - Event creation with proper timezone handling
    - Duplicate detection by title + datetime
    - Token refresh handling

    Setup: Use Google Cloud Console to create OAuth credentials.
    API: https://developers.google.com/calendar/api/v3/reference
    """
    async def authenticate(self, credentials): raise NotImplementedError
    async def create_event(self, event_data): raise NotImplementedError
    async def update_event(self, event_id, event_data): raise NotImplementedError
    async def check_duplicate(self, event_data): raise NotImplementedError

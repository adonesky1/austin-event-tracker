import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventCategory(str, enum.Enum):
    MUSIC = "music"
    ARTS = "arts"
    FESTIVALS = "festivals"
    THEATRE = "theatre"
    KIDS = "kids"
    OUTDOOR = "outdoor"
    SEASONAL = "seasonal"
    COMMUNITY = "community"


class SourceType(str, enum.Enum):
    API = "api"
    FEED = "feed"
    SCRAPER = "scraper"


class BudgetLevel(str, enum.Enum):
    FREE = "free"
    LOW = "low"
    MODERATE = "moderate"
    ANY = "any"


class CrowdSensitivity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FeedbackType(str, enum.Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    MORE_LIKE_THIS = "more_like_this"
    LESS_LIKE_THIS = "less_like_this"
    TOO_FAR = "too_far"
    TOO_EXPENSIVE = "too_expensive"
    WRONG_AGE = "wrong_age"
    ALREADY_KNEW = "already_knew"


class DigestStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"


class SourceHealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"


class SyncRunStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

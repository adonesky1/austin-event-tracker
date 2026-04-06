import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, EventCategory, SourceType, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[EventCategory] = mapped_column(Enum(EventCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100))
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(50), default="America/Chicago")
    venue_name: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    age_suitability: Mapped[str | None] = mapped_column(String(50))
    family_score: Mapped[float | None] = mapped_column(Float)
    image_url: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    dedupe_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    canonical_event_url: Mapped[str | None] = mapped_column(Text)
    editorial_summary: Mapped[str | None] = mapped_column(Text)
    relevance_explanation: Mapped[str | None] = mapped_column(Text)

    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")


class EventSource(Base):
    __tablename__ = "event_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id")
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, values_callable=lambda obj: [e.value for e in obj]))
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    title: Mapped[str | None] = mapped_column(Text)
    start_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue_name: Mapped[str | None] = mapped_column(String(255))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    event: Mapped[Event | None] = relationship(back_populates="sources")

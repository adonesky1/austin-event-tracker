import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RawEvent(BaseModel):
    source_name: str
    source_type: str
    source_url: str | None = None
    title: str
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    venue_name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    city: str
    latitude: float | None = None
    longitude: float | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str = "USD"
    age_suitability: str | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    canonical_event_url: str | None = None
    raw_payload: dict | None = None


class NormalizedEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    description: str | None = None
    category: str = "community"
    subcategory: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    timezone: str = "America/Chicago"
    venue_name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    city: str
    latitude: float | None = None
    longitude: float | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str = "USD"
    age_suitability: str | None = None
    family_score: float | None = None
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    dedupe_group_id: uuid.UUID | None = None
    canonical_event_url: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    editorial_summary: str | None = None
    relevance_explanation: str | None = None

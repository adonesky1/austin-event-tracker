import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.base import TrackedItemKind


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    city: str = "austin"
    adults: list[dict] = Field(default_factory=list)
    children: list[dict] = Field(default_factory=list)
    preferred_neighborhoods: list[str] = Field(default_factory=list)
    max_distance_miles: int = 30
    preferred_days: list[str] = Field(default_factory=list)
    preferred_times: list[str] = Field(default_factory=list)
    budget: str = "moderate"
    interests: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    max_events_per_digest: int = 15
    crowd_sensitivity: str = "medium"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserProfileUpdate(BaseModel):
    email: str | None = None
    city: str | None = None
    adults: list[dict] | None = None
    children: list[dict] | None = None
    preferred_neighborhoods: list[str] | None = None
    max_distance_miles: int | None = None
    preferred_days: list[str] | None = None
    preferred_times: list[str] | None = None
    budget: str | None = None
    interests: list[str] | None = None
    dislikes: list[str] | None = None
    max_events_per_digest: int | None = None
    crowd_sensitivity: str | None = None


class PromptConfigResponse(BaseModel):
    key: str
    system_prompt: str
    user_prompt_template: str
    is_default: bool = False
    updated_at: datetime | None = None


class PromptConfigUpdate(BaseModel):
    system_prompt: str
    user_prompt_template: str


class TrackedItemCreate(BaseModel):
    label: str
    kind: TrackedItemKind
    enabled: bool = True
    boost_weight: float = 0.15
    notes: str | None = None


class TrackedItemUpdate(BaseModel):
    label: str | None = None
    kind: TrackedItemKind | None = None
    enabled: bool | None = None
    boost_weight: float | None = None
    notes: str | None = None


class TrackedItemResponse(BaseModel):
    id: uuid.UUID
    label: str
    kind: str
    enabled: bool
    boost_weight: float
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

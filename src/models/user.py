import uuid

from sqlalchemy import ARRAY, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, BudgetLevel, CrowdSensitivity, TimestampMixin


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="austin")
    adults: Mapped[dict | None] = mapped_column(JSONB)
    children: Mapped[dict | None] = mapped_column(JSONB)
    preferred_neighborhoods: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_distance_miles: Mapped[int] = mapped_column(Integer, default=30)
    preferred_days: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    preferred_times: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    budget: Mapped[BudgetLevel] = mapped_column(Enum(BudgetLevel), default=BudgetLevel.MODERATE)
    interests: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    dislikes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_events_per_digest: Mapped[int] = mapped_column(Integer, default=15)
    crowd_sensitivity: Mapped[CrowdSensitivity] = mapped_column(
        Enum(CrowdSensitivity), default=CrowdSensitivity.MEDIUM
    )

import uuid

from sqlalchemy import Boolean, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, TrackedItemKind


class TrackedItem(Base, TimestampMixin):
    __tablename__ = "tracked_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[TrackedItemKind] = mapped_column(Enum(TrackedItemKind, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    boost_weight: Mapped[float] = mapped_column(Float, default=0.15)
    notes: Mapped[str | None] = mapped_column(Text)

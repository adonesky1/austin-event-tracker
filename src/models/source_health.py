import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, SourceHealthStatus


class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SourceHealthStatus] = mapped_column(
        Enum(SourceHealthStatus, values_callable=lambda obj: [e.value for e in obj]), default=SourceHealthStatus.HEALTHY
    )

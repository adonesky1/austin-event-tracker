import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, DigestStatus


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id")
    )
    subject: Mapped[str] = mapped_column(Text)
    html_content: Mapped[str] = mapped_column(Text)
    plaintext_content: Mapped[str] = mapped_column(Text)
    event_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[DigestStatus] = mapped_column(
        Enum(DigestStatus), default=DigestStatus.DRAFT
    )
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

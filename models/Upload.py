from __future__ import annotations
import uuid
from datetime import datetime
from models import Base
from sqlalchemy import String, Text, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cv_path: Mapped[str] = mapped_column(String, nullable=False)
    report_path: Mapped[str] = mapped_column(String, nullable=False)
    cv_text: Mapped[str | None] = mapped_column(Text)
    project_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    jobs: Mapped[list["Job"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    __table_args__ = (
    Index("ix_uploads_created", "created_at"),
)
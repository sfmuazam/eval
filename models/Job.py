from __future__ import annotations
from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import Enum, Text, ForeignKey, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from models import Base
from models.Enums import JobStatus

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.queued, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)

    upload = relationship("Upload", back_populates="jobs")

    result: Mapped[Optional["Result"]] = relationship("Result", back_populates="job", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

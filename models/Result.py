from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from models import Base


class Result(Base):
    __tablename__ = "results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    cv_match_rate: Mapped[float | None] = mapped_column() # 0..100
    project_score: Mapped[float | None] = mapped_column() # 1..5 or 0..10
    cv_feedback: Mapped[str | None] = mapped_column(Text)
    project_feedback: Mapped[str | None] = mapped_column(Text)
    overall_summary: Mapped[str | None] = mapped_column(Text)
    detail_scores: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    job: Mapped["Job"] = relationship(back_populates="result")
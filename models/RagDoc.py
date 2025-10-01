from __future__ import annotations
import os
import uuid
from datetime import datetime

from sqlalchemy import Enum, String, Text, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from models import Base
from .Enums import RagDocType

VECTOR_DIM = int(os.getenv("EMBED_DIM", "768"))

class RagDoc(Base):
    __tablename__ = "rag_docs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[RagDocType] = mapped_column(Enum(RagDocType, name="rag_doc_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(VECTOR_DIM))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_rag_docs_type", "type"),
        Index("ix_rag_docs_tags", "tags", postgresql_using="gin"),
    )

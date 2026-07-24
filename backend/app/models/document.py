"""Document — 05_Database_Design.md, extended with confidence-pipeline fields."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import DocumentProcessingStatus
from app.models.mixins import UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "documents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )

    # Added in M2 — the frozen schema had no way to record who uploaded a
    # document, but M2's DoD requires linking documents to both Company
    # and User.
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    document_type: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, name="document_processing_status"),
        default=DocumentProcessingStatus.PENDING,
    )

    # Confidence pipeline additions (recent schema update)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

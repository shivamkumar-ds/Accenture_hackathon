"""
Shared model mixins.

UUIDPrimaryKeyMixin — every table in 05_Database_Design.md uses a UUID
primary key ("Database Constraints: Primary keys are UUIDs"). Defined
once here so it isn't repeated in every model file.

CapabilityMetadataMixin — the six fields from 05_Database_Design.md's
"Common Metadata" section, shared by Certification, Employee, Project,
Equipment, and FinancialRecord. Defined once so the five capability
entity models inherit identical behavior instead of repeating columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums import VerificationStatus


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class CapabilityMetadataMixin:
    """Common Metadata (05_Database_Design.md) — shared by all five capability entities."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="capability_verification_status"),
        default=VerificationStatus.PENDING,
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    # M9 — soft-delete, applying the Database Design's already-frozen
    # Active/Archived/Deleted principle to a domain (capability entities)
    # that had never needed it until now. NULL = active.
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

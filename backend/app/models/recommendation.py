"""Recommendation and ComplianceMatrix — 05_Database_Design.md, extended with confidence propagation and verification fields."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ComplianceMatrixVerificationStatus, MatchStatus, RecommendationType, RiskLevel
from app.models.mixins import UUIDPrimaryKeyMixin


class Recommendation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "recommendations"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True
    )
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type"), nullable=False
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(RiskLevel, name="risk_level"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Confidence propagation — replaces the single `confidence` field (D-106 / recent schema update).
    document_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    entity_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    matching_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    recommendation_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capability_snapshots.id"), nullable=True
    )


class ComplianceMatrix(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "compliance_matrix"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=False, index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False, index=True
    )
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus, name="match_status"), nullable=False)
    supporting_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification & confidence additions (recent schema update).
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(RiskLevel, name="risk_level"), nullable=True
    )
    verification_status: Mapped[ComplianceMatrixVerificationStatus] = mapped_column(
        Enum(ComplianceMatrixVerificationStatus, name="compliance_matrix_verification_status"),
        default=ComplianceMatrixVerificationStatus.PENDING,
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matching_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_reference: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

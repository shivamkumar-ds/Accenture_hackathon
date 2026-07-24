"""Pydantic schemas for Decision Intelligence — Compliance Matrix, Recommendation, Gap Analysis."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    CapabilityEntityType,
    ComplianceMatrixVerificationStatus,
    MatchStatus,
    RecommendationType,
    RequirementType,
    RiskLevel,
)


class EvidenceSourceRead(BaseModel):
    """
    Resolves ComplianceMatrix.evidence_reference (a CapabilityMapping id,
    opaque to the frontend) into the actual company record and source
    document that grounds a recommendation — the "Company Document" leg of
    the Decision Screen's signature evidence trail (DESIGN_SYSTEM.md §10:
    Recommendation -> Evidence -> Source Clause -> Company Document). Built
    by decision_service.resolve_evidence_sources() at response time; never
    stored — the underlying CapabilityMapping row is the source of truth.
    """

    entity_type: CapabilityEntityType
    label: str
    source_document_id: uuid.UUID | None
    source_document_name: str | None


class ComplianceMatrixEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    status: MatchStatus
    supporting_evidence: str | None
    notes: str | None
    requires_verification: bool
    verification_reason: str | None
    risk_level: RiskLevel | None
    verification_status: ComplianceMatrixVerificationStatus
    matching_confidence: float | None
    evidence_reference: uuid.UUID | None
    # Added for the Decision Screen evidence trail (see DESIGN_SYSTEM.md
    # §10) — not present on the ComplianceMatrix ORM row itself, so these
    # two are NOT populated via model_validate()'s from_attributes; the
    # router attaches them explicitly via model_copy(update=...) once it
    # has looked up the owning Requirement and resolved the evidence
    # source. Both are optional and default to None so this stays a pure
    # additive change to the wire contract.
    source_page: int | None = None
    evidence_source: EvidenceSourceRead | None = None


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    recommendation_type: RecommendationType
    executive_summary: str | None
    risk_level: RiskLevel | None
    generated_at: datetime
    document_confidence: float | None
    entity_confidence: float | None
    matching_confidence: float | None
    recommendation_confidence: float | None
    overall_confidence: float | None
    snapshot_id: uuid.UUID | None


class GapAnalysisEntry(BaseModel):
    """Computed at response time from the Compliance Matrix, not a stored table — same
    principle as M4's freshness: derived data, not a new persistence concept."""

    requirement_id: uuid.UUID
    requirement_type: RequirementType
    description: str | None
    mandatory: bool
    status: MatchStatus
    reason: str | None
    source_page: int | None = None


class EvaluationResponse(BaseModel):
    recommendation: RecommendationRead
    compliance_matrix: list[ComplianceMatrixEntryRead]
    gap_analysis: list[GapAnalysisEntry]

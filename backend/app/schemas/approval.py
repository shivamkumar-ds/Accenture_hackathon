"""Pydantic schemas for the Human Approval Layer."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import BusinessDecision, ComplianceMatrixVerificationStatus
from app.schemas.decision import ComplianceMatrixEntryRead, RecommendationRead
from app.schemas.mission import MissionRead


class VerifyComplianceRequest(BaseModel):
    """A human's own determination on a specific flagged compliance row —
    not a checkbox, a recorded judgment. PENDING is not a valid target
    value here; that's the starting state, not something a human "verifies" to."""

    verification_status: ComplianceMatrixVerificationStatus
    note: str | None = None

    @model_validator(mode="after")
    def _reject_pending(self) -> "VerifyComplianceRequest":
        if self.verification_status == ComplianceMatrixVerificationStatus.PENDING:
            raise ValueError("verification_status must be a real determination, not PENDING.")
        return self


class ApprovalDecisionRequest(BaseModel):
    mission_id: uuid.UUID
    decision: BusinessDecision
    reason: str | None = None

    @model_validator(mode="after")
    def _require_reason_for_rejected(self) -> "ApprovalDecisionRequest":
        if self.decision == BusinessDecision.REJECTED and not (self.reason and self.reason.strip()):
            raise ValueError("A reason is required when the decision is 'rejected'.")
        return self


class DecisionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID | None
    event: str
    result: str | None
    timestamp: datetime
    # Additive (TENDER_JOURNEY_IMPLEMENTATION_PLAN.md Phase 6) -- resolved
    # read-time only from user_id, same pattern already used for
    # ComplianceMatrixEntryRead.verified_by_name. Not populated by
    # model_validate() directly (AuditLog has no such column); the router
    # attaches it via model_copy(update=...) after a batch User lookup.
    # Defaults to None so this stays backward-compatible with any other
    # caller that constructs a DecisionEventRead without it.
    user_name: str | None = None


class ApprovalHistoryResponse(BaseModel):
    mission: MissionRead
    recommendation: RecommendationRead
    compliance_matrix: list[ComplianceMatrixEntryRead]
    decision_events: list[DecisionEventRead]

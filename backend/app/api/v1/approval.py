"""
Human Approval Layer API.

POST /compliance/{id}/verify is a new endpoint (not in the frozen API
doc — a genuine gap, same precedent as /auth/register and
/missions/{id}/execute). POST /approval and GET /approval/{mission_id}
match 06_API_Design.md directly.

POST /approval is also the backend for the "Bid Decision" feature
(docs/BID_DECISION_DESIGN.md) — that design doc originally proposed a
new PATCH /missions/{id}/decision endpoint before discovering this one
already implemented the same contract. record_decision() is Bid
Decision's write path; get_approval_history()'s decision_events is its
audit trail.

This router never calls tender_service or decision_service — it only
governs the lifecycle of a recommendation that already exists.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_approver, require_business_decision_permission
from app.core.database import get_db
from app.models import User
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalHistoryResponse,
    DecisionEventRead,
    VerifyComplianceRequest,
)
from app.schemas.decision import ComplianceMatrixEntryRead, RecommendationRead
from app.schemas.mission import MissionRead
from app.services import approval_service, decision_service

compliance_router = APIRouter(prefix="/compliance", tags=["approval"])
approval_router = APIRouter(prefix="/approval", tags=["approval"])


@compliance_router.post("/{compliance_id}/verify", response_model=ComplianceMatrixEntryRead)
def verify_compliance_row(
    compliance_id: uuid.UUID,
    payload: VerifyComplianceRequest,
    current_user: User = Depends(require_approver),
    db: Session = Depends(get_db),
) -> ComplianceMatrixEntryRead:
    row = approval_service.verify_compliance_row(
        db, compliance_id, current_user.company_id, current_user.id,
        payload.verification_status, payload.note,
    )
    verifier_names = decision_service.resolve_verifier_names(db, [row])
    return ComplianceMatrixEntryRead.model_validate(row).model_copy(
        update={"verified_by_name": verifier_names.get(row.verified_by)}
    )


@approval_router.post("", response_model=MissionRead)
def record_decision(
    payload: ApprovalDecisionRequest,
    current_user: User = Depends(require_business_decision_permission),
    db: Session = Depends(get_db),
) -> MissionRead:
    mission = approval_service.record_decision(
        db, payload.mission_id, current_user.company_id, current_user.id,
        payload.decision, payload.reason,
    )
    return MissionRead.model_validate(mission)


@approval_router.get("/{mission_id}", response_model=ApprovalHistoryResponse)
def get_approval_history(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApprovalHistoryResponse:
    mission, recommendation, compliance_rows, decision_events = approval_service.get_approval_history(
        db, mission_id, current_user.company_id
    )

    # Decision History (TENDER_JOURNEY_IMPLEMENTATION_PLAN.md Phase 6) --
    # DecisionEventRead.user_id is a raw UUID; resolve it to a display name
    # the same way verify_compliance_row() above already resolves
    # verified_by_name -- one small batch query, read-time only, tolerant
    # of a user whose account no longer resolves (skipped, not raised).
    user_ids = {e.user_id for e in decision_events if e.user_id is not None}
    user_names: dict[uuid.UUID, str] = {}
    if user_ids:
        user_names = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    return ApprovalHistoryResponse(
        mission=MissionRead.model_validate(mission),
        recommendation=RecommendationRead.model_validate(recommendation),
        compliance_matrix=[ComplianceMatrixEntryRead.model_validate(r) for r in compliance_rows],
        decision_events=[
            DecisionEventRead.model_validate(e).model_copy(update={"user_name": user_names.get(e.user_id)})
            for e in decision_events
        ],
    )

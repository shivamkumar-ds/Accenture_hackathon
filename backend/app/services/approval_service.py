"""
Approval service — the Human Approval Layer.

Never calls tender_service or decision_service — this module only
reads the existing Recommendation/ComplianceMatrix and writes
verification/decision facts. AI recommends, humans decide; nothing here
regenerates anything M6 or M7 already produced.

Company scoping for ComplianceMatrix rows goes through
ComplianceMatrix -> Recommendation -> Mission -> company_id (two hops,
since ComplianceMatrix has no company_id of its own).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditLog, ComplianceMatrix, Mission, Recommendation
from app.models.enums import BusinessDecision, ComplianceMatrixVerificationStatus, MissionStatus, RiskLevel
from app.services.exceptions import ConflictError, NotFoundError

APPROVAL_AGENT = "human_approval_layer"

# Only these decisions end a mission — NEEDS_REVISION deliberately does
# not, since its entire purpose is "send this back for further work."
TERMINAL_DECISIONS = {BusinessDecision.PROCEED, BusinessDecision.REJECTED}

# Only rows both flagged for verification AND at HIGH/CRITICAL risk block
# a decision — per the approved refinement, MEDIUM/LOW verification stays
# advisory, not a hard gate.
BLOCKING_RISK_LEVELS = {RiskLevel.HIGH, RiskLevel.CRITICAL}


def _log(db: Session, mission_id: uuid.UUID, user_id: uuid.UUID | None, event: str, result: str = "") -> None:
    db.add(AuditLog(mission_id=mission_id, user_id=user_id, agent=APPROVAL_AGENT, event=event, result=result))
    db.commit()


from app.services import mission_service


def _get_compliance_row_scoped(db: Session, compliance_id: uuid.UUID, company_id: uuid.UUID) -> ComplianceMatrix:
    row = (
        db.query(ComplianceMatrix)
        .join(Recommendation, ComplianceMatrix.recommendation_id == Recommendation.id)
        .join(Mission, Recommendation.mission_id == Mission.id)
        .filter(ComplianceMatrix.id == compliance_id, Mission.company_id == company_id)
        .one_or_none()
    )
    if row is None:
        raise NotFoundError(f"Compliance matrix entry '{compliance_id}' not found.")
    return row


def get_blocking_rows(db: Session, recommendation_id: uuid.UUID) -> list[ComplianceMatrix]:
    return (
        db.query(ComplianceMatrix)
        .filter(
            ComplianceMatrix.recommendation_id == recommendation_id,
            ComplianceMatrix.requires_verification.is_(True),
            ComplianceMatrix.risk_level.in_(BLOCKING_RISK_LEVELS),
            ComplianceMatrix.verified_by.is_(None),
        )
        .all()
    )


def verify_compliance_row(
    db: Session,
    compliance_id: uuid.UUID,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    verification_status: ComplianceMatrixVerificationStatus,
    note: str | None,
) -> ComplianceMatrix:
    row = _get_compliance_row_scoped(db, compliance_id, company_id)

    mission = (
        db.query(Mission)
        .join(Recommendation, Recommendation.mission_id == Mission.id)
        .filter(Recommendation.id == row.recommendation_id)
        .one()
    )
    if mission.status != MissionStatus.AWAITING_APPROVAL:
        # Interpretive addition, not explicitly requested: a finalized
        # mission's evidence is historical and shouldn't be editable
        # after the fact — matches the "nothing overwrites historical
        # recommendations" principle applied to the evidence backing them.
        raise ConflictError(
            f"Mission '{mission.id}' is not awaiting approval (status: {mission.status.value}) — "
            "compliance rows cannot be verified after a mission has been finalized."
        )

    row.verification_status = verification_status
    row.verified_by = user_id
    row.verified_at = datetime.now(timezone.utc)
    if note:
        row.notes = f"{row.notes or ''} | Human verification: {note}".strip(" |")

    db.commit()
    db.refresh(row)

    _log(
        db, mission.id, user_id,
        f"Compliance row {row.id} verified as {verification_status.value}",
        note or "",
    )
    return row


def record_decision(
    db: Session, mission_id: uuid.UUID, company_id: uuid.UUID, user_id: uuid.UUID,
    decision: BusinessDecision, reason: str | None,
) -> Mission:
    mission = mission_service.get_mission(db, mission_id, company_id)

    if mission.status != MissionStatus.AWAITING_APPROVAL:
        raise ConflictError(
            f"Mission '{mission_id}' is not awaiting approval (current status: {mission.status.value}). "
            "A decision can only be recorded once, immediately after a recommendation exists; "
            "re-approval, approval after a prior decision, and approval on a mission that hasn't "
            "reached evaluation yet are all rejected here."
        )
    if mission.recommendation_id is None:
        raise NotFoundError(f"Mission '{mission_id}' has no recommendation to act on.")

    blocking_rows = get_blocking_rows(db, mission.recommendation_id)
    if blocking_rows:
        row_ids = ", ".join(str(r.id) for r in blocking_rows)
        raise ConflictError(
            f"{len(blocking_rows)} high-risk compliance item(s) still require verification "
            f"before a decision can be finalized: {row_ids}."
        )

    if decision in TERMINAL_DECISIONS:
        mission.status = MissionStatus.COMPLETED
        mission.completed_at = datetime.now(timezone.utc)
    # NEEDS_REVISION: mission deliberately stays AWAITING_APPROVAL — not terminal.

    db.commit()
    db.refresh(mission)

    # Bug #004: logged AFTER the mission's own commit succeeds, not before.
    # This used to write "Decision recorded" to AuditLog (its own commit,
    # inside _log()) *before* the mission.status mutation was ever
    # committed. If that second commit had then failed for any reason, the
    # audit trail would have permanently and misleadingly claimed a
    # business decision was recorded when the mission's actual status
    # never changed — a false record, which is exactly the failure mode a
    # compliance/audit trail feature cannot tolerate. Matches the ordering
    # verify_compliance_row() above already uses: commit the real state
    # change first, log it only once that's actually true.
    _log(db, mission.id, user_id, f"Decision recorded: {decision.value}", reason or "")
    return mission


def get_approval_history(db: Session, mission_id: uuid.UUID, company_id: uuid.UUID):
    mission = mission_service.get_mission(db, mission_id, company_id)
    if mission.recommendation_id is None:
        raise NotFoundError(f"Mission '{mission_id}' has no recommendation yet.")
    recommendation = db.get(Recommendation, mission.recommendation_id)
    compliance_rows = (
        db.query(ComplianceMatrix).filter(ComplianceMatrix.recommendation_id == recommendation.id).all()
    )
    decision_events = (
        db.query(AuditLog)
        .filter(AuditLog.mission_id == mission.id, AuditLog.agent == APPROVAL_AGENT)
        .order_by(AuditLog.timestamp)
        .all()
    )
    return mission, recommendation, compliance_rows, decision_events

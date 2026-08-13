"""
Regression coverage for Bug #004 (docs/BUG_BUCKET.md): approval_service.record_decision()
used to write the "Decision recorded" AuditLog entry (its own commit, inside _log())
*before* committing the mission's actual status change. If that second commit ever
failed, the audit trail would permanently and misleadingly show a decision was recorded
that never actually took effect -- a false record, which a compliance/audit-trail
feature cannot tolerate.

This test forces exactly that failure (the mission-state commit raises) and proves the
fix: no audit log entry is written unless the mission's own state change actually
committed successfully first.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import AuditLog, ComplianceMatrix, Company, Mission, Recommendation, User
from app.models.enums import BusinessDecision, MissionStatus, RiskLevel, UserRole, UserStatus
from app.services import approval_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__, User.__table__, Mission.__table__, Recommendation.__table__,
            ComplianceMatrix.__table__, AuditLog.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_failed_mission_commit_leaves_no_misleading_audit_entry(db, monkeypatch):
    from app.models.enums import RecommendationType

    company = Company(id=uuid.uuid4(), name="Acme", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    mission = Mission(
        id=uuid.uuid4(), company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.AWAITING_APPROVAL,
    )
    db.add(mission)
    db.flush()
    recommendation = Recommendation(
        id=uuid.uuid4(), mission_id=mission.id, recommendation_type=RecommendationType.GO,
        executive_summary="Looks good", risk_level=RiskLevel.LOW,
        document_confidence=0.9, entity_confidence=0.9, matching_confidence=0.9,
        recommendation_confidence=0.9, overall_confidence=0.9,
    )
    db.add(recommendation)
    db.flush()
    mission.recommendation_id = recommendation.id
    db.commit()

    # Force the mission-state commit to fail -- simulates a transient DB
    # error (dropped connection, etc.) at exactly the point the real
    # status transition would be persisted.
    real_commit = db.commit
    call_count = {"n": 0}

    def _failing_commit():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated: commit failed")
        return real_commit()

    monkeypatch.setattr(db, "commit", _failing_commit)

    with pytest.raises(RuntimeError):
        approval_service.record_decision(
            db, mission.id, company.id, user.id, BusinessDecision.PROCEED, "Looks solid"
        )

    monkeypatch.undo()  # restore real commit so we can query cleanly below
    db.rollback()

    audit_entries = db.query(AuditLog).filter(AuditLog.mission_id == mission.id).all()
    assert audit_entries == [], (
        "No audit log entry should exist for a decision that was never actually "
        "committed -- an entry here would be a false record."
    )

    db.refresh(mission)
    assert mission.status == MissionStatus.AWAITING_APPROVAL  # unchanged, exactly as it should be

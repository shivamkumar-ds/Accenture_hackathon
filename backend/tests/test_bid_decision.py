"""
Bid Decision feature (docs/BID_DECISION_DESIGN.md) regression tests.

Service-layer tests over approval_service.record_decision(), same
in-memory-SQLite / real-ORM pattern already used in
test_multi_tenancy.py and test_decision_engine_concurrency.py. Not
blanket coverage -- one test per contract guarantee the design doc and
the frozen architecture actually depend on:

- the three-value BusinessDecision vocabulary is honored (not the AI's
  own RecommendationType),
- PROCEED/REJECTED are terminal (mission -> completed), NEEDS_REVISION
  is not (mission stays awaiting_approval),
- a reason is mandatory for REJECTED, optional otherwise,
- an unverified HIGH/CRITICAL compliance row blocks the decision
  entirely -- the "human below, but not a rubber stamp" guarantee.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import ARRAY

from app.core.database import Base
from app.models import (
    Company,
    ComplianceMatrix,
    Mission,
    Recommendation,
    Requirement,
    Tender,
    User,
)
from app.models.enums import (
    BusinessDecision,
    MatchStatus,
    MissionStatus,
    RecommendationType,
    RequirementType,
    RiskLevel,
    UserRole,
    UserStatus,
)
from app.services import approval_service
from app.services.exceptions import ConflictError


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__, User.__table__, Mission.__table__, Tender.__table__,
            Requirement.__table__, Recommendation.__table__, ComplianceMatrix.__table__,
            __import__("app.models", fromlist=["AuditLog"]).AuditLog.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def mission_with_recommendation(db):
    company = Company(id=uuid.uuid4(), name="Co", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Exec", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.EXECUTIVE, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    mission = Mission(
        id=uuid.uuid4(), company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.AWAITING_APPROVAL,
    )
    db.add(mission)
    db.flush()
    tender = Tender(id=uuid.uuid4(), mission_id=mission.id, tender_name="T")
    db.add(tender)
    db.flush()
    requirement = Requirement(id=uuid.uuid4(), tender_id=tender.id, requirement_type=RequirementType.ELIGIBILITY)
    db.add(requirement)
    db.flush()
    recommendation = Recommendation(
        id=uuid.uuid4(), mission_id=mission.id, recommendation_type=RecommendationType.GO,
    )
    db.add(recommendation)
    mission.recommendation_id = recommendation.id
    db.flush()
    db.commit()
    return {"company": company, "user": user, "mission": mission, "recommendation": recommendation,
            "requirement": requirement}


def _add_compliance_row(db, recommendation_id, requirement_id, *, risk_level, requires_verification, verified):
    from app.models.enums import ComplianceMatrixVerificationStatus

    row = ComplianceMatrix(
        id=uuid.uuid4(), recommendation_id=recommendation_id, requirement_id=requirement_id,
        status=MatchStatus.REVIEW_REQUIRED, risk_level=risk_level,
        requires_verification=requires_verification,
        # get_blocking_rows() gates on verified_by IS NULL, not on
        # verification_status -- a row is only "unblocked" once a human
        # has actually verified it.
        verified_by=uuid.uuid4() if verified else None,
        verification_status=(
            ComplianceMatrixVerificationStatus.VERIFIED_COMPLIANT if verified
            else ComplianceMatrixVerificationStatus.PENDING
        ),
    )
    db.add(row)
    db.commit()
    return row


class TestBusinessDecisionTransitions:
    def test_proceed_completes_the_mission(self, db, mission_with_recommendation):
        ctx = mission_with_recommendation
        mission = approval_service.record_decision(
            db, ctx["mission"].id, ctx["company"].id, ctx["user"].id,
            BusinessDecision.PROCEED, None,
        )
        assert mission.status == MissionStatus.COMPLETED
        assert mission.completed_at is not None

    def test_rejected_completes_the_mission(self, db, mission_with_recommendation):
        ctx = mission_with_recommendation
        mission = approval_service.record_decision(
            db, ctx["mission"].id, ctx["company"].id, ctx["user"].id,
            BusinessDecision.REJECTED, "Capacity risk too high.",
        )
        assert mission.status == MissionStatus.COMPLETED
        assert mission.completed_at is not None

    def test_needs_revision_leaves_mission_awaiting_approval(self, db, mission_with_recommendation):
        ctx = mission_with_recommendation
        mission = approval_service.record_decision(
            db, ctx["mission"].id, ctx["company"].id, ctx["user"].id,
            BusinessDecision.NEEDS_REVISION, "Need updated pricing before proceeding.",
        )
        assert mission.status == MissionStatus.AWAITING_APPROVAL
        assert mission.completed_at is None


class TestBlockingComplianceRows:
    def test_unverified_high_risk_row_blocks_the_decision(self, db, mission_with_recommendation):
        ctx = mission_with_recommendation
        _add_compliance_row(
            db, ctx["recommendation"].id, ctx["requirement"].id,
            risk_level=RiskLevel.HIGH, requires_verification=True, verified=False,
        )
        with pytest.raises(ConflictError):
            approval_service.record_decision(
                db, ctx["mission"].id, ctx["company"].id, ctx["user"].id,
                BusinessDecision.PROCEED, None,
            )

    def test_verified_high_risk_row_does_not_block(self, db, mission_with_recommendation):
        ctx = mission_with_recommendation
        _add_compliance_row(
            db, ctx["recommendation"].id, ctx["requirement"].id,
            risk_level=RiskLevel.HIGH, requires_verification=True, verified=True,
        )
        mission = approval_service.record_decision(
            db, ctx["mission"].id, ctx["company"].id, ctx["user"].id,
            BusinessDecision.PROCEED, None,
        )
        assert mission.status == MissionStatus.COMPLETED


class TestApprovalDecisionRequestValidation:
    def test_reason_required_for_rejected(self):
        from pydantic import ValidationError

        from app.schemas.approval import ApprovalDecisionRequest

        with pytest.raises(ValidationError):
            ApprovalDecisionRequest(mission_id=uuid.uuid4(), decision=BusinessDecision.REJECTED, reason=None)

    def test_reason_optional_for_proceed_and_needs_revision(self):
        from app.schemas.approval import ApprovalDecisionRequest

        for decision in (BusinessDecision.PROCEED, BusinessDecision.NEEDS_REVISION):
            ApprovalDecisionRequest(mission_id=uuid.uuid4(), decision=decision, reason=None)


class TestBusinessDecisionPermission:
    def test_executive_and_administrator_have_permission(self):
        from app.api.deps import user_can_make_business_decision

        class _StubUser:
            def __init__(self, role):
                self.role = role

        assert user_can_make_business_decision(_StubUser(UserRole.EXECUTIVE)) is True
        assert user_can_make_business_decision(_StubUser(UserRole.ADMINISTRATOR)) is True
        assert user_can_make_business_decision(_StubUser(UserRole.BID_MANAGER)) is False
        assert user_can_make_business_decision(_StubUser(UserRole.AUDITOR)) is False

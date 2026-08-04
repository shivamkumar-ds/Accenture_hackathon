"""
Regression coverage for Bug #002 (docs/BUG_BUCKET.md): tender_service.run_analysis()
used to look up the tender's Document and resolve its storage path *outside*
the try/except that handles analysis failures. If that document lookup ever
came back None, the service raised a bare AttributeError -- an unclean 500 --
and, worse, left Tender.processing_status stuck at PROCESSING forever, since
nothing on that path ever set it to FAILED.

Not reachable through the normal upload flow (a Tender's Document is never
hard-deleted while still referenced), but the goal of the backend
stabilization audit is that every endpoint either succeeds or fails with a
clean business error -- a raw crash with no failed-state transition violates
that even if it's presently unreachable in practice. This test proves the
fix: a missing Document now raises ExtractionError and the tender ends up in
FAILED (retryable), not stuck.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Company, Mission, Requirement, Tender, User
from app.models.enums import DocumentProcessingStatus, MissionStatus, UserRole, UserStatus
from app.services import tender_service
from app.services.exceptions import ExtractionError


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, User.__table__, Mission.__table__, Tender.__table__, Requirement.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_company_and_user(db):
    company = Company(id=uuid.uuid4(), name="Acme", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return company, user


@pytest.mark.asyncio
async def test_run_analysis_with_missing_document_fails_cleanly_not_stuck(db):
    company, user = _make_company_and_user(db)
    mission = Mission(
        id=uuid.uuid4(), company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.CREATED,
    )
    db.add(mission)
    db.flush()

    # Deliberately reference a Document row that does not exist -- the
    # invariant that Documents are never hard-deleted while referenced is
    # what normally prevents this, but the service must still fail cleanly
    # if that invariant is ever violated, instead of crashing with a raw
    # AttributeError and leaving the tender stuck in PROCESSING.
    tender = Tender(
        id=uuid.uuid4(), mission_id=mission.id, tender_name="Orphaned Tender",
        organization="Test Org", uploaded_document=uuid.uuid4(),
        processing_status=DocumentProcessingStatus.PENDING.value,
    )
    db.add(tender)
    db.commit()

    with pytest.raises(ExtractionError):
        await tender_service.run_analysis(db, tender.id, company.id)

    db.refresh(tender)
    assert tender.processing_status == DocumentProcessingStatus.FAILED.value

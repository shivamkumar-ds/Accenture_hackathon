"""
Regression coverage for the "delete a failed tender" scenario reported
4 August 2026 (investigated as a possible bug distinct from Bug #001 --
docs/BUG_BUCKET.md).

Reproduces, with real service-layer code against an in-memory SQLite
database (same pattern as test_multi_tenancy.py): a tender whose
analysis genuinely fails (Tender.processing_status -> "failed",
Mission.status reverts to "created" -- there is no FAILED value in the
frozen MissionStatus enum, by design), then deleted (archived).

Conclusion of the investigation: this workflow does not crash the
backend, does not orphan any row, and does not affect any other
mission or company. The originally reported "Tender Workspace stopped
working, even for other accounts" symptom cannot be produced by this
path at all -- archive_mission() and list_missions() are both scoped
to a single company_id, so nothing here can touch another company's
data. That symptom (every account affected simultaneously) is the
signature of a schema-level failure -- exactly what Bug #001 was. This
test exists to keep that conclusion permanently verified: if a future
change ever makes deleting a failed tender crash or leak into other
missions, this test catches it immediately.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import AuditLog, Company, Document, Mission, Requirement, Tender, User
from app.models.enums import DocumentProcessingStatus, MissionStatus, UserRole, UserStatus
from app.services import mission_service
from app.services.exceptions import ExtractionError


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__, User.__table__, Mission.__table__, Tender.__table__,
            Requirement.__table__, Document.__table__, AuditLog.__table__,
        ],
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


def _make_tender_mission(db, company, user, tender_name="Broken Tender"):
    # A real, already-persisted Document -- upload_tender() always creates
    # this before the Tender ever exists, so a Tender with no valid
    # uploaded_document is not a reachable state through the real flow.
    document = Document(
        id=uuid.uuid4(), company_id=company.id, uploaded_by=user.id, document_type="tender",
        file_name="broken.pdf", storage_path=f"{company.id}/documents/{uuid.uuid4()}.pdf",
    )
    db.add(document)
    db.flush()

    mission = Mission(
        id=uuid.uuid4(), company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.CREATED,
    )
    db.add(mission)
    db.flush()

    tender = Tender(
        id=uuid.uuid4(), mission_id=mission.id, tender_name=tender_name,
        organization="Test Org", uploaded_document=document.id,
        processing_status=DocumentProcessingStatus.PENDING.value,
    )
    db.add(tender)
    db.commit()
    return mission, tender, document


def _fail_analysis(db, mission, company, user):
    """Drives execute_mission() through a genuine analysis failure --
    the same code path a corrupt/unparseable uploaded PDF triggers."""
    with patch(
        "app.agents.tender_analyzer.analyze_tender",
        new=AsyncMock(side_effect=RuntimeError("simulated: cannot parse PDF")),
    ):
        with pytest.raises(ExtractionError):
            asyncio.run(mission_service.execute_mission(db, mission.id, company.id, user.id))


def test_failed_analysis_sets_expected_status_with_no_orphans(db):
    company, user = _make_company_and_user(db)
    mission, tender, _document = _make_tender_mission(db, company, user)

    _fail_analysis(db, mission, company, user)

    db.refresh(mission)
    db.refresh(tender)
    assert mission.status == MissionStatus.CREATED  # reverted, safe to retry -- no FAILED value exists
    assert tender.processing_status == DocumentProcessingStatus.FAILED.value
    assert db.query(Requirement).filter(Requirement.tender_id == tender.id).count() == 0


def test_deleting_a_failed_tender_does_not_raise(db):
    company, user = _make_company_and_user(db)
    mission, tender, document = _make_tender_mission(db, company, user)
    _fail_analysis(db, mission, company, user)

    archived = mission_service.archive_mission(db, mission.id, company.id)

    assert archived.status == MissionStatus.ARCHIVED
    # The document is never touched by archiving a mission -- deleting is
    # a soft-delete of the Mission only.
    still_present = db.query(Document).filter(Document.id == document.id).one_or_none()
    assert still_present is not None
    assert still_present.removed_at is None


def test_listing_missions_after_deleting_a_failed_tender_does_not_raise(db):
    company, user = _make_company_and_user(db)
    mission, tender, _document = _make_tender_mission(db, company, user)
    _fail_analysis(db, mission, company, user)
    mission_service.archive_mission(db, mission.id, company.id)

    missions = mission_service.list_missions(db, company.id)  # must not raise

    assert len(missions) == 1
    assert missions[0].status == MissionStatus.ARCHIVED


def test_deleting_a_failed_tender_never_affects_another_company(db):
    """The originally reported symptom was Tender Workspace breaking for
    *other accounts too*. Company scoping alone makes that structurally
    impossible from this workflow -- proven here, not just asserted."""
    company_a, user_a = _make_company_and_user(db)
    company_b, user_b = _make_company_and_user(db)

    mission_a, tender_a, _doc_a = _make_tender_mission(db, company_a, user_a, "A's Broken Tender")
    mission_b, tender_b, _doc_b = _make_tender_mission(db, company_b, user_b, "B's Healthy Tender")

    _fail_analysis(db, mission_a, company_a, user_a)
    mission_service.archive_mission(db, mission_a.id, company_a.id)

    # Company B's own list is completely unaffected by Company A's failed
    # tender and its deletion.
    company_b_missions = mission_service.list_missions(db, company_b.id)
    assert len(company_b_missions) == 1
    assert company_b_missions[0].id == mission_b.id
    assert company_b_missions[0].status == MissionStatus.CREATED

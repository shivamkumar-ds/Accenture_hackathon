"""
Multi-tenancy regression tests (RC-2 remediation, requested explicitly:
"I do not want blanket coverage... These tests are intended to permanently
protect one of BidOps' core security guarantees.").

Not blanket coverage -- five focused checks, one per entity category named
in the remediation instructions: Company A must never be able to read
Company B's Documents, Missions, Tenders, Evaluations, or Capability
entities. Each test also confirms the positive path (Company A CAN read
its own data), so a test that only ever asserted "access denied" couldn't
accidentally pass by coincidence (e.g. a bug that denies everyone).

Service-layer tests, not API/HTTP-layer -- this is where the actual
isolation logic lives (verified directly in the RC-2 audit by reading
every relevant service function), and it matches the existing, previously
-endorsed pattern in scripts/verify_evidence_trail.py: real ORM objects,
real service-layer code, an in-memory SQLite database built from the
project's own Base/session pattern. No FastAPI TestClient involved, so
these are also unaffected by the rate limiting added alongside this suite.
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
    Certification,
    Company,
    Document,
    Employee,
    Equipment,
    FinancialRecord,
    Mission,
    Project,
    Recommendation,
    Requirement,
    Tender,
    User,
)

# sqlite has no native ARRAY/JSONB support -- Employee.skills and
# Project.similarity_tags use postgres ARRAY, and find_capability_by_id()
# unconditionally queries all five capability tables (Certification,
# Employee, Project, Equipment, FinancialRecord), so all five must be
# creatable even though this file's tests only ever populate Certification
# rows. Same shim as test_decision_engine_concurrency.py; test-only,
# production always runs against real Postgres.


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"
from app.models.enums import (
    DocumentProcessingStatus,
    MissionStatus,
    RecommendationType,
    RiskLevel,
    UserRole,
    UserStatus,
)
from app.services import capability_service, decision_service, document_service, mission_service, tender_service
from app.services.exceptions import NotFoundError


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__, User.__table__, Mission.__table__, Tender.__table__,
            Requirement.__table__, Document.__table__, Certification.__table__,
            Employee.__table__, Project.__table__, Equipment.__table__, FinancialRecord.__table__,
            Recommendation.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_company(db, name: str) -> Company:
    company = Company(id=uuid.uuid4(), name=name, registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    return company


def _make_user(db, company: Company) -> User:
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def two_companies(db):
    """Two independent tenants, each with a user -- everything below is
    scoped to one or the other, never shared."""
    company_a = _make_company(db, "Company A")
    company_b = _make_company(db, "Company B")
    user_a = _make_user(db, company_a)
    user_b = _make_user(db, company_b)
    db.commit()
    return {"a": company_a, "b": company_b, "user_a": user_a, "user_b": user_b}


class TestDocumentIsolation:
    def test_cannot_read_another_companys_document(self, db, two_companies):
        doc = Document(
            id=uuid.uuid4(), company_id=two_companies["a"].id, uploaded_by=two_companies["user_a"].id,
            document_type="certification", file_name="cert.pdf", storage_path="a/documents/cert.pdf",
        )
        db.add(doc)
        db.commit()

        # Positive path: Company A can read its own document.
        assert document_service.get_document(db, doc.id, two_companies["a"].id).id == doc.id

        # Negative path: Company B gets NotFoundError, not the document.
        with pytest.raises(NotFoundError):
            document_service.get_document(db, doc.id, two_companies["b"].id)


class TestMissionIsolation:
    def test_cannot_read_another_companys_mission(self, db, two_companies):
        mission = Mission(
            id=uuid.uuid4(), company_id=two_companies["a"].id, user_id=two_companies["user_a"].id,
            mission_type="tender_evaluation", status=MissionStatus.CREATED,
        )
        db.add(mission)
        db.commit()

        assert mission_service.get_mission(db, mission.id, two_companies["a"].id).id == mission.id

        with pytest.raises(NotFoundError):
            mission_service.get_mission(db, mission.id, two_companies["b"].id)


class TestTenderIsolation:
    def test_cannot_read_another_companys_tender(self, db, two_companies):
        mission = Mission(
            id=uuid.uuid4(), company_id=two_companies["a"].id, user_id=two_companies["user_a"].id,
            mission_type="tender_evaluation", status=MissionStatus.CREATED,
        )
        db.add(mission)
        db.flush()
        tender = Tender(
            id=uuid.uuid4(), mission_id=mission.id, tender_name="Confidential Tender",
            processing_status=DocumentProcessingStatus.COMPLETED.value,
        )
        db.add(tender)
        db.commit()

        assert tender_service.get_tender(db, tender.id, two_companies["a"].id).id == tender.id

        with pytest.raises(NotFoundError):
            tender_service.get_tender(db, tender.id, two_companies["b"].id)


class TestEvaluationIsolation:
    def test_cannot_read_another_companys_evaluation(self, db, two_companies):
        mission = Mission(
            id=uuid.uuid4(), company_id=two_companies["a"].id, user_id=two_companies["user_a"].id,
            mission_type="tender_evaluation", status=MissionStatus.AWAITING_APPROVAL,
        )
        db.add(mission)
        db.flush()

        # A real Recommendation row, not just an empty mission -- proves the
        # isolation check happens before recommendation data is ever
        # touched, not as a side effect of "no recommendation exists yet."
        recommendation = Recommendation(
            id=uuid.uuid4(), mission_id=mission.id, recommendation_type=RecommendationType.GO,
            executive_summary="Confidential summary", risk_level=RiskLevel.LOW,
            document_confidence=0.9, entity_confidence=0.9, matching_confidence=0.9,
            recommendation_confidence=0.9, overall_confidence=0.9,
        )
        db.add(recommendation)
        db.flush()
        mission.recommendation_id = recommendation.id
        db.commit()

        assert decision_service.get_evaluation(db, mission.id, two_companies["a"].id).id == recommendation.id

        with pytest.raises(NotFoundError):
            decision_service.get_evaluation(db, mission.id, two_companies["b"].id)


class TestCapabilityEntityIsolation:
    def test_cannot_read_another_companys_capability_entity(self, db, two_companies):
        cert = Certification(
            id=uuid.uuid4(), company_id=two_companies["a"].id, certification_name="ISO 9001",
        )
        db.add(cert)
        db.commit()

        found = capability_service.find_capability_by_id(db, cert.id, two_companies["a"].id)
        assert found is not None and found[1].id == cert.id

        # find_capability_by_id returns None (not an exception) for a
        # cross-tenant lookup -- the API layer maps that to a 404, same
        # externally-visible "not found" behavior as every other category
        # above, just a different internal shape. See
        # app/services/capability_service.py::find_capability_by_id.
        assert capability_service.find_capability_by_id(db, cert.id, two_companies["b"].id) is None

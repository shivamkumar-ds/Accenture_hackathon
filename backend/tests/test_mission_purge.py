"""
Regression coverage for mission_service.purge_mission() -- the real,
permanent deletion added alongside archive_mission() (soft-delete) so an
already-archived tender in the Tender Workspace can be genuinely removed,
not just hidden. Every FK in this schema is the Postgres default RESTRICT
(no ON DELETE CASCADE anywhere) -- purge_mission() has to delete/detach
every dependent row itself, in an order that satisfies each constraint.
This suite builds the full real dependency graph (Tender, Requirement,
CapabilityMapping, Recommendation, ComplianceMatrix, CapabilitySnapshot,
Document, AuditLog, LLMCallEvent) and asserts:
  - purge is blocked unless the mission is already ARCHIVED,
  - every genuinely dependent row is actually gone afterward,
  - AuditLog/LLMCallEvent rows are preserved (detached, not destroyed) --
    the deliberate exception, per purge_mission()'s own docstring,
  - company scoping still applies (can't purge another company's mission),
  - and the whole thing runs cleanly against SQLite (no FK-order bugs),
    though the specific "no ON DELETE CASCADE" schema property this
    function works around is itself a Postgres-only concept -- SQLite's
    own FK enforcement is off by default and not what's being validated
    here; what's validated is purge_mission()'s own delete ordering.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    AuditLog,
    CapabilityMapping,
    CapabilitySnapshot,
    Company,
    ComplianceMatrix,
    Document,
    LLMCallEvent,
    Mission,
    Recommendation,
    Requirement,
    Tender,
    User,
)
from app.models.enums import (
    CapabilityEntityType,
    DocumentProcessingStatus,
    MatchStatus,
    MissionStatus,
    RecommendationType,
    RequirementType,
    UserRole,
    UserStatus,
)
from app.services import mission_service
from app.services.exceptions import ConflictError, NotFoundError

# sqlite has no native JSONB support (CapabilitySnapshot.snapshot_data) --
# render it as JSON under sqlite so an in-memory test database can be
# created at all. Same limitation/workaround as
# test_decision_engine_concurrency.py; test-only, production always runs
# against real Postgres.


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__, User.__table__, Mission.__table__, Tender.__table__,
            Requirement.__table__, CapabilityMapping.__table__, Document.__table__,
            Recommendation.__table__, ComplianceMatrix.__table__, CapabilitySnapshot.__table__,
            AuditLog.__table__, LLMCallEvent.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()

    # storage.delete_file() is a real filesystem/GCS call -- not relevant
    # to what this test validates (the DB-level purge ordering), and no
    # document actually exists on disk for these synthetic rows. Same
    # single-seam-mock pattern used throughout this test suite.
    monkeypatch.setattr(mission_service.storage, "delete_file", lambda _path: None)

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


def _build_full_mission_graph(db, company, user, status=MissionStatus.ARCHIVED) -> dict:
    """
    One Mission with a real dependent row in every table purge_mission()
    has to reason about. Every id used below is assigned explicitly
    up front and returned as a plain dict of UUIDs (not ORM instances) --
    SQLAlchemy expires every loaded object's attributes after a commit by
    default, and purge_mission() itself commits; holding onto and later
    re-reading an attribute (even just `.id`) on an object whose row that
    same commit just deleted raises ObjectDeletedError. Plain UUIDs
    sidestep that entirely and are all a test needs anyway.
    """
    ids = {
        "document": uuid.uuid4(), "mission": uuid.uuid4(), "tender": uuid.uuid4(),
        "requirement": uuid.uuid4(), "capability_mapping": uuid.uuid4(),
        "capability_snapshot": uuid.uuid4(), "recommendation": uuid.uuid4(),
        "compliance_row": uuid.uuid4(), "audit_log": uuid.uuid4(), "llm_event": uuid.uuid4(),
    }

    document = Document(
        id=ids["document"], company_id=company.id, uploaded_by=user.id, document_type="tender",
        file_name="tender.pdf", storage_path=f"{company.id}/documents/{uuid.uuid4()}.pdf",
    )
    db.add(document)

    mission = Mission(
        id=ids["mission"], company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=status,
    )
    db.add(mission)

    tender = Tender(
        id=ids["tender"], mission_id=ids["mission"], tender_name="Test Tender",
        organization="Test Org", uploaded_document=ids["document"],
        processing_status=DocumentProcessingStatus.COMPLETED.value,
    )
    db.add(tender)

    document.tender_id = ids["tender"]
    document.document_role = "main"

    requirement = Requirement(
        id=ids["requirement"], tender_id=ids["tender"], requirement_type=RequirementType.ELIGIBILITY,
        description="Must be registered", mandatory=True, source_page=1,
        source_document_id=ids["document"], confidence=0.9,
    )
    db.add(requirement)

    capability_mapping = CapabilityMapping(
        id=ids["capability_mapping"], requirement_id=ids["requirement"],
        capability_entity_type=CapabilityEntityType.CERTIFICATION,
        capability_entity_id=uuid.uuid4(), match_status=MatchStatus.MET,
    )
    db.add(capability_mapping)

    capability_snapshot = CapabilitySnapshot(
        id=ids["capability_snapshot"], mission_id=ids["mission"], snapshot_version=1,
        snapshot_data={"foo": "bar"},
    )
    db.add(capability_snapshot)

    recommendation = Recommendation(
        id=ids["recommendation"], mission_id=ids["mission"], recommendation_type=RecommendationType.GO,
        executive_summary="Looks good", snapshot_id=ids["capability_snapshot"],
    )
    db.add(recommendation)

    compliance_row = ComplianceMatrix(
        id=ids["compliance_row"], recommendation_id=ids["recommendation"], requirement_id=ids["requirement"],
        status=MatchStatus.MET,
    )
    db.add(compliance_row)

    audit_log = AuditLog(
        id=ids["audit_log"], mission_id=ids["mission"], user_id=user.id, agent="test", event="did a thing",
    )
    db.add(audit_log)

    llm_event = LLMCallEvent(
        id=ids["llm_event"], company_id=company.id, mission_id=ids["mission"], purpose="test",
        provider="mock", model="mock-model", latency_ms=10, success=True,
    )
    db.add(llm_event)

    db.flush()
    # Mission's forward pointers set only after the rows they point to
    # exist -- assigned via update() (not attribute assignment + commit)
    # so this function never needs to touch the `mission` object again
    # after this point either.
    db.query(Mission).filter(Mission.id == ids["mission"]).update(
        {Mission.capability_snapshot_id: ids["capability_snapshot"], Mission.recommendation_id: ids["recommendation"]}
    )
    db.commit()
    return ids


def test_purge_blocked_unless_mission_is_archived(db):
    company, user = _make_company_and_user(db)
    ids = _build_full_mission_graph(db, company, user, status=MissionStatus.CREATED)

    with pytest.raises(ConflictError):
        mission_service.purge_mission(db, ids["mission"], company.id)

    # Nothing was touched by the rejected attempt.
    assert db.get(Mission, ids["mission"]) is not None


def test_purge_deletes_the_full_dependency_graph(db):
    company, user = _make_company_and_user(db)
    ids = _build_full_mission_graph(db, company, user, status=MissionStatus.ARCHIVED)

    mission_service.purge_mission(db, ids["mission"], company.id)

    assert db.get(Mission, ids["mission"]) is None
    assert db.get(Tender, ids["tender"]) is None
    assert db.get(Requirement, ids["requirement"]) is None
    assert db.get(CapabilityMapping, ids["capability_mapping"]) is None
    assert db.get(Document, ids["document"]) is None
    assert db.get(Recommendation, ids["recommendation"]) is None
    assert db.get(ComplianceMatrix, ids["compliance_row"]) is None
    assert db.get(CapabilitySnapshot, ids["capability_snapshot"]) is None


def test_purge_detaches_but_preserves_audit_and_telemetry_history(db):
    company, user = _make_company_and_user(db)
    ids = _build_full_mission_graph(db, company, user, status=MissionStatus.ARCHIVED)

    mission_service.purge_mission(db, ids["mission"], company.id)

    surviving_audit_log = db.get(AuditLog, ids["audit_log"])
    assert surviving_audit_log is not None
    assert surviving_audit_log.mission_id is None
    assert surviving_audit_log.event == "did a thing"  # content untouched, only the FK detached

    surviving_llm_event = db.get(LLMCallEvent, ids["llm_event"])
    assert surviving_llm_event is not None
    assert surviving_llm_event.mission_id is None


def test_purge_does_not_touch_another_companys_mission(db):
    company_a, user_a = _make_company_and_user(db)
    company_b, _user_b = _make_company_and_user(db)
    ids = _build_full_mission_graph(db, company_a, user_a, status=MissionStatus.ARCHIVED)

    with pytest.raises(NotFoundError):
        mission_service.purge_mission(db, ids["mission"], company_b.id)

    assert db.get(Mission, ids["mission"]) is not None


def test_purge_mission_with_no_tender_still_works(db):
    """A mission that never got as far as having a Tender (edge case, not
    reachable through the normal upload flow, but purge_mission() must
    not crash on an empty dependency graph)."""
    company, user = _make_company_and_user(db)
    mission_id = uuid.uuid4()
    mission = Mission(
        id=mission_id, company_id=company.id, user_id=user.id,
        mission_type="tender_evaluation", status=MissionStatus.ARCHIVED,
    )
    db.add(mission)
    db.commit()

    mission_service.purge_mission(db, mission_id, company.id)

    assert db.get(Mission, mission_id) is None

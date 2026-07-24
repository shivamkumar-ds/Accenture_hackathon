"""
Evidence-trail provenance verification (D-145) -- a developer utility, NOT a
pytest test file (deliberately not named test_*.py, and lives under
scripts/, alongside vertex_smoke_check.py, outside anything pytest.ini
points at) so it is never auto-collected or auto-run by `pytest` in CI.

Purpose: prove the complete Recommendation -> Evidence -> Source Clause ->
Company Document pipeline (DESIGN_SYSTEM.md §10's signature Decision Screen
chain; PRODUCT_CONSTITUTION.md §7's Evidence First principle) actually works
against real ORM objects and their real relationships -- not just "the
schema compiles" or "the OpenAPI spec lists the fields."

DB setup: this repo has no tests/conftest.py and no DB-backed test fixtures
at all (checked directly -- tests/agents/test_llm_client.py is pure unit
tests, no database). So this script builds a temporary in-memory SQLite
database using the project's own Base/session pattern from
app/core/database.py -- the same declarative Base and sessionmaker shape
the real app uses, just pointed at sqlite:///:memory: instead of Postgres.
This is not a new architecture; it is the existing pattern, minimally
instantiated. Table selection is deliberately narrowed to only the tables
this scenario touches, because a handful of columns elsewhere
(postgresql.ARRAY, postgresql.JSONB) don't compile under sqlite and aren't
needed here.

Exercises the real production code path directly -- decision_service.
resolve_evidence_sources() and app.api.v1.evaluation._build_response() --
never a reimplementation of their logic.

Usage (from the BidOps backend venv):

    python scripts/verify_evidence_trail.py

Exits 0 if every assertion passes, 1 otherwise.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.evaluation import _build_response
from app.core.database import Base
from app.models import (
    CapabilityMapping,
    Certification,
    Company,
    ComplianceMatrix,
    Document,
    Mission,
    Recommendation,
    Requirement,
    Tender,
    User,
)
from app.models.enums import (
    CapabilityEntityType,
    MatchStatus,
    RecommendationType,
    RequirementType,
    UserRole,
)
from app.services import decision_service

results: list[tuple[str, bool]] = []


def check(label: str, condition: bool) -> None:
    results.append((label, condition))
    print(("PASS  " if condition else "FAIL  ") + label)


# ---------------------------------------------------------------------------
# 1. Minimum valid dataset -- temporary in-memory DB, project's own pattern.
# ---------------------------------------------------------------------------
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(
    bind=engine,
    tables=[
        Company.__table__,
        User.__table__,
        Mission.__table__,
        Tender.__table__,
        Requirement.__table__,
        Certification.__table__,
        Document.__table__,
        Recommendation.__table__,
        CapabilityMapping.__table__,
        ComplianceMatrix.__table__,
    ],
)
db = sessionmaker(bind=engine)()

company = Company(name="Test Co", registration_number="REG-1")
db.add(company)
db.flush()

user = User(company_id=company.id, name="Verifier", email="verifier@test.com", password_hash="x", role=UserRole.ADMINISTRATOR)
db.add(user)
db.flush()

mission = Mission(company_id=company.id, user_id=user.id, mission_type="tender_evaluation")
db.add(mission)
db.flush()

tender = Tender(mission_id=mission.id, tender_name="Test Tender", organization="Test Org")
db.add(tender)
db.flush()

requirement = Requirement(
    tender_id=tender.id,
    requirement_type=RequirementType.CERTIFICATION,
    description="Bidder must hold a valid ISO 9001 certification.",
    mandatory=True,
    source_page=42,
)
db.add(requirement)
db.flush()

document = Document(
    company_id=company.id,
    uploaded_by=user.id,
    document_type="certification",
    file_name="iso_9001_certificate.pdf",
    storage_path="/tmp/iso_9001_certificate.pdf",
)
db.add(document)
db.flush()

certification = Certification(
    company_id=company.id,
    certification_name="ISO 9001:2015",
    source_document_id=document.id,
)
db.add(certification)
db.flush()

recommendation = Recommendation(mission_id=mission.id, recommendation_type=RecommendationType.GO)
db.add(recommendation)
db.flush()

mapping = CapabilityMapping(
    requirement_id=requirement.id,
    capability_entity_type=CapabilityEntityType.CERTIFICATION,
    capability_entity_id=certification.id,
    match_status=MatchStatus.MET,
)
db.add(mapping)
db.flush()

compliance_row = ComplianceMatrix(
    recommendation_id=recommendation.id,
    requirement_id=requirement.id,
    status=MatchStatus.MET,
    supporting_evidence="ISO 9001:2015 certification on file, issued and currently valid.",
    evidence_reference=mapping.id,
)
db.add(compliance_row)
db.commit()

# ---------------------------------------------------------------------------
# 2. Call the real production functions.
# ---------------------------------------------------------------------------
resolved = decision_service.resolve_evidence_sources(db, [compliance_row])
response = _build_response(db, recommendation, [compliance_row], {requirement.id: requirement})
entry = response.compliance_matrix[0]

print("\n--- resolve_evidence_sources() direct call ---")
check("resolve_evidence_sources() returns an entry for this mapping", mapping.id in resolved)

print("\n--- Full pipeline: Recommendation ---")
check("Recommendation is present in the response", response.recommendation is not None)
check("Recommendation.id matches the DB row (correct IDs)", response.recommendation.id == recommendation.id)
check("Recommendation.mission_id matches the DB row (correct IDs)", response.recommendation.mission_id == mission.id)
check("Recommendation.recommendation_type is not null", response.recommendation.recommendation_type is not None)

print("\n--- Full pipeline: Evidence ---")
check("supporting_evidence is present, not null", entry.supporting_evidence is not None)
check("supporting_evidence text is correct, not fabricated", entry.supporting_evidence == compliance_row.supporting_evidence)

print("\n--- Full pipeline: Source Clause (tender page) ---")
check("source_page is present, not null", entry.source_page is not None)
check("source_page value is correct", entry.source_page == 42)

print("\n--- Full pipeline: Company Document provenance ---")
check("evidence_source is present, not null", entry.evidence_source is not None)
check("evidence_source.entity_type is correct", entry.evidence_source.entity_type == CapabilityEntityType.CERTIFICATION)
check("evidence_source.label is correct, not fabricated", entry.evidence_source.label == "ISO 9001:2015")
check("evidence_source.source_document_id matches the DB row (correct IDs)", entry.evidence_source.source_document_id == document.id)
check("evidence_source.source_document_name is correct file name", entry.evidence_source.source_document_name == "iso_9001_certificate.pdf")

print("\n--- Full pipeline: identifiers linking every step ---")
check("compliance_matrix entry.requirement_id matches the DB row (correct IDs)", entry.requirement_id == requirement.id)
check("compliance_matrix entry.evidence_reference matches the mapping id (correct IDs)", entry.evidence_reference == mapping.id)

# ---------------------------------------------------------------------------
# 3. Negative paths: "return null rather than fabricating data" must hold.
# ---------------------------------------------------------------------------
print("\n--- Negative paths: null-safety, no fabrication ---")

req_no_evidence = Requirement(tender_id=tender.id, requirement_type=RequirementType.DEADLINE, source_page=3)
db.add(req_no_evidence)
db.flush()
row_no_evidence = ComplianceMatrix(
    recommendation_id=recommendation.id, requirement_id=req_no_evidence.id,
    status=MatchStatus.REVIEW_REQUIRED, evidence_reference=None,
)
db.add(row_no_evidence)
db.commit()
resp_no_evidence = _build_response(db, recommendation, [row_no_evidence], {req_no_evidence.id: req_no_evidence})
entry_no_evidence = resp_no_evidence.compliance_matrix[0]
check("No evidence_reference -> evidence_source is null (no fabrication)", entry_no_evidence.evidence_source is None)
check("source_page still resolves independently of evidence_source", entry_no_evidence.source_page == 3)

req_dangling = Requirement(tender_id=tender.id, requirement_type=RequirementType.CERTIFICATION, source_page=99)
db.add(req_dangling)
db.flush()
mapping_dangling = CapabilityMapping(
    requirement_id=req_dangling.id, capability_entity_type=CapabilityEntityType.CERTIFICATION,
    capability_entity_id=uuid.uuid4(),  # no Certification row has this id
    match_status=MatchStatus.NOT_MET,
)
db.add(mapping_dangling)
db.flush()
row_dangling = ComplianceMatrix(
    recommendation_id=recommendation.id, requirement_id=req_dangling.id,
    status=MatchStatus.NOT_MET, evidence_reference=mapping_dangling.id,
)
db.add(row_dangling)
db.commit()
resp_dangling = _build_response(db, recommendation, [row_dangling], {req_dangling.id: req_dangling})
entry_dangling = resp_dangling.compliance_matrix[0]
check("Unresolvable cited entity -> evidence_source is null, no exception raised", entry_dangling.evidence_source is None)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
passed = sum(1 for _, ok in results if ok)
failed = len(results) - passed
print(f"\n{'=' * 60}\n{passed}/{len(results)} PASSED, {failed} FAILED\n{'=' * 60}")
sys.exit(1 if failed else 0)

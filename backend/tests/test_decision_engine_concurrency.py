"""
Verifies the RC-2 remediation (finding H-3) to
decision_service.run_evaluation(): per-requirement LLM matching now runs
with bounded concurrency instead of fully sequentially.

Uses a hand-written tracking fake LLM client, not MockLLMClient, so the
test can directly observe concurrency behavior (how many calls are ever
in flight at once, and total wall-clock time) rather than only checking
that the final result is correct. Sequential execution and this bounded-
concurrency implementation would both produce the same final database
rows -- the thing that actually changed, and the thing worth a real
regression test, is the *timing and concurrency* behavior itself.

Also verifies the three things the founder's remediation instructions
explicitly required stay unchanged: result ordering (each ComplianceMatrix
row still maps back to the correct originating requirement), evidence
mapping (matched_entity_id / confidence propagate the same way), and
error-handling semantics (one failed match still fails the whole
evaluation with the same ExtractionError, not a partial success).
"""

import asyncio
import json
import time
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import ARRAY

from app.agents import decision_engine
from app.core.config import get_settings
from app.core.database import Base
from app.models import (
    CapabilityMapping,
    CapabilitySnapshot,
    Certification,
    Company,
    ComplianceMatrix,
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
from app.models.enums import MissionStatus, RequirementType, UserRole, UserStatus
from app.services import decision_service
from app.services.exceptions import ExtractionError

# sqlite has no native ARRAY/JSONB support (both are postgres-specific types
# used by Employee.skills/Project.similarity_tags and
# CapabilitySnapshot.snapshot_data) -- render them as JSON under sqlite so
# an in-memory test database can be created at all. Test-only; production
# always runs against real Postgres. Same limitation documented in
# scripts/verify_evidence_trail.py, which sidesteps it by never touching
# these three columns; this test can't avoid it since run_evaluation()
# always writes a CapabilitySnapshot and always reads every capability
# table via capability_service.list_capabilities().


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


NUM_REQUIREMENTS = 8


class _TrackingLLMClient:
    """Records concurrency depth and timing; deterministic 'met' response."""

    def __init__(self, delay: float = 0.05, fail_on_call: int | None = None):
        self.in_flight = 0
        self.max_in_flight = 0
        self.call_count = 0
        self.delay = delay
        self.fail_on_call = fail_on_call
        self._lock = asyncio.Lock()

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        async with self._lock:
            self.call_count += 1
            this_call = self.call_count
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            if self.fail_on_call is not None and this_call == self.fail_on_call:
                raise RuntimeError("simulated transient LLM failure")
            return json.dumps({"status": "met", "matched_entity_index": 0, "reasoning": "test"})
        finally:
            async with self._lock:
                self.in_flight -= 1


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            User.__table__,
            Mission.__table__,
            Tender.__table__,
            Requirement.__table__,
            Document.__table__,
            Certification.__table__,
            Employee.__table__,
            Project.__table__,
            Equipment.__table__,
            FinancialRecord.__table__,
            CapabilitySnapshot.__table__,
            Recommendation.__table__,
            CapabilityMapping.__table__,
            ComplianceMatrix.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def fixtures(db_session):
    """One company, one user, one mission/tender with NUM_REQUIREMENTS
    CERTIFICATION requirements, and one Certification candidate to match
    against -- enough to exercise the real LLM-call path (not the
    zero-candidates deterministic shortcut in decision_engine.match_requirement)."""
    company = Company(id=uuid.uuid4(), name="Acme Co", registration_number=str(uuid.uuid4()))
    db_session.add(company)
    db_session.flush()

    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    mission = Mission(id=uuid.uuid4(), company_id=company.id, user_id=user.id,
                       mission_type="tender_evaluation", status=MissionStatus.RUNNING)
    db_session.add(mission)
    db_session.flush()

    tender = Tender(id=uuid.uuid4(), mission_id=mission.id, tender_name="Test Tender",
                     processing_status="completed")
    db_session.add(tender)
    db_session.flush()

    for i in range(NUM_REQUIREMENTS):
        db_session.add(Requirement(
            id=uuid.uuid4(), tender_id=tender.id, requirement_type=RequirementType.CERTIFICATION,
            description=f"Requirement {i}", mandatory=False, source_page=1, confidence=0.9,
        ))

    db_session.add(Certification(
        id=uuid.uuid4(), company_id=company.id, certification_name="ISO 9001",
        confidence_score=0.95,
    ))
    db_session.commit()
    return {"company": company, "mission": mission}


@pytest.mark.asyncio
async def test_evaluation_runs_with_bounded_concurrency(db_session, fixtures, monkeypatch):
    tracker = _TrackingLLMClient(delay=0.05)
    monkeypatch.setattr(decision_engine, "get_llm_client", lambda *_: tracker)

    max_concurrency = get_settings().decision_engine_max_concurrency

    start = time.monotonic()
    recommendation = await decision_service.run_evaluation(
        db_session, fixtures["mission"].id, fixtures["company"].id
    )
    elapsed = time.monotonic() - start

    assert tracker.call_count == NUM_REQUIREMENTS, "every requirement should still trigger exactly one match call"

    # Bounded: never more concurrent calls in flight than the configured limit.
    assert tracker.max_in_flight <= max_concurrency

    # Actually concurrent: more than one call in flight at once (not
    # accidentally serialized back to the old sequential behavior).
    assert tracker.max_in_flight > 1

    # Meaningfully faster than fully sequential would be. Sequential:
    # NUM_REQUIREMENTS * delay = 8 * 0.05 = 0.4s. With max_concurrency=5,
    # 8 requirements need ceil(8/5)=2 batches ~= 0.1s. Generous margin for
    # test-environment scheduling jitter.
    sequential_estimate = NUM_REQUIREMENTS * tracker.delay
    assert elapsed < sequential_estimate * 0.75, (
        f"expected meaningfully faster than sequential ({sequential_estimate:.2f}s), got {elapsed:.2f}s"
    )

    # Ordering/evidence-mapping preserved: one ComplianceMatrix row per
    # requirement, each correctly tagged with its own requirement_id (not
    # scrambled or collapsed by running concurrently).
    rows = (
        db_session.query(ComplianceMatrix)
        .filter(ComplianceMatrix.recommendation_id == recommendation.id)
        .all()
    )
    assert len(rows) == NUM_REQUIREMENTS
    requirement_ids_on_rows = {row.requirement_id for row in rows}
    all_requirements = db_session.query(Requirement).all()
    assert requirement_ids_on_rows == {r.id for r in all_requirements}
    assert all(row.evidence_reference is not None for row in rows), "the single Certification candidate should have been matched for every row"


@pytest.mark.asyncio
async def test_evaluation_preserves_fail_whole_run_semantics(db_session, fixtures, monkeypatch):
    """One failing match still fails the entire evaluation (same behavior
    as the old sequential loop's try/except), not a partial success."""
    tracker = _TrackingLLMClient(delay=0.01, fail_on_call=3)
    monkeypatch.setattr(decision_engine, "get_llm_client", lambda *_: tracker)

    with pytest.raises(ExtractionError):
        await decision_service.run_evaluation(db_session, fixtures["mission"].id, fixtures["company"].id)

    # Nothing should have been persisted -- the whole reasoning phase
    # completes (or fails) entirely in memory before any DB write begins.
    assert db_session.query(Recommendation).count() == 0
    assert db_session.query(ComplianceMatrix).count() == 0

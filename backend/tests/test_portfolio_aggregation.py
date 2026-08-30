"""
Regression coverage for Portfolio aggregation (app/services/portfolio_service.py,
app/api/v1/portfolio.py) — approved implementation plan, Phase 2.

Covers:
- Distinct-mission counting for the flagship insight (a mission with
  multiple gaps of the same requirement_type counts once).
- Tied requirement types combined into one insight sentence, never an
  arbitrary pick.
- Archived-mission exclusion, matching Dashboard.tsx's existing convention.
- Not-yet-analyzed vs. unable-to-load isolation (one broken mission never
  crashes the whole response).
- Bucket mapping for all four RecommendationType values, and that
  confidence never promotes a NO_GO above a GO (buckets are structurally
  disjoint, not confidence-ordered against each other).
- QualificationOverride semantics: an override can move a mission's live
  bucket, but the structural gap the insight counts is read from
  remediation_summary.qualification_gaps, which stays populated regardless
  of override -- so the insight's affected-mission count is unchanged.
- Multi-tenant isolation.
- No LLM call anywhere in the Portfolio code path.
- Insight numbers are computed from seeded data, never hard-coded.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.agents import decision_engine
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    BidReadinessConfirmation,
    Company,
    ComplianceMatrix,
    Mission,
    QualificationOverride,
    Recommendation,
    Requirement,
    Tender,
    User,
)
from app.models.enums import MatchStatus, MissionStatus, RecommendationType, RequirementType, RiskLevel, UserRole, UserStatus

ALL_TABLES = [
    Company.__table__, User.__table__, Mission.__table__, Tender.__table__,
    Requirement.__table__, Recommendation.__table__, ComplianceMatrix.__table__,
    QualificationOverride.__table__, BidReadinessConfirmation.__table__,
]


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=ALL_TABLES)
    TestSession = sessionmaker(bind=engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(main_module.settings, "migration_guard_enabled", False)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


def _seeded_session(engine_client):
    override = engine_client.app.dependency_overrides[get_db]
    gen = override()
    return next(gen)


def _auth_headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _seed_company_and_admin(db):
    company = Company(id=uuid.uuid4(), name=f"Co-{uuid.uuid4()}", registration_number=str(uuid.uuid4()))
    db.add(company)
    db.flush()
    user = User(
        id=uuid.uuid4(), company_id=company.id, name="Admin", email=f"{uuid.uuid4()}@example.com",
        password_hash="x", role=UserRole.ADMINISTRATOR, status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return company, user


def _seed_mission_with_tender(db, company, user, *, status=MissionStatus.AWAITING_APPROVAL, tender_name="T"):
    mission = Mission(id=uuid.uuid4(), company_id=company.id, user_id=user.id, mission_type="tender_evaluation", status=status)
    db.add(mission)
    db.flush()
    tender = Tender(id=uuid.uuid4(), mission_id=mission.id, tender_name=tender_name)
    db.add(tender)
    db.flush()
    return mission, tender


def _seed_requirement(db, tender, *, requirement_type=RequirementType.CERTIFICATION, mandatory=True, description="Requirement"):
    # requirement_nature left None deliberately -- resolve_evaluation_nature()
    # defaults a non-procedural requirement_type to CAPABILITY_CLAIM, the
    # exact real-world default for every historical/most current rows
    # (see that function's own docstring). Not set explicitly here so
    # these tests exercise the real default path, not a special case.
    requirement = Requirement(id=uuid.uuid4(), tender_id=tender.id, requirement_type=requirement_type, mandatory=mandatory, description=description)
    db.add(requirement)
    db.flush()
    return requirement


def _seed_recommendation(db, mission, *, recommendation_type=RecommendationType.GO, overall_confidence=0.8):
    recommendation = Recommendation(
        id=uuid.uuid4(), mission_id=mission.id, recommendation_type=recommendation_type,
        executive_summary="seeded", risk_level=RiskLevel.LOW,
        document_confidence=0.9, entity_confidence=0.9, matching_confidence=0.9,
        recommendation_confidence=0.9, overall_confidence=overall_confidence,
    )
    db.add(recommendation)
    db.flush()
    mission.recommendation_id = recommendation.id
    db.commit()
    return recommendation


def _seed_compliance_row(db, recommendation, requirement, *, status=MatchStatus.NOT_MET, requirement_id_override=None):
    row = ComplianceMatrix(
        id=uuid.uuid4(), recommendation_id=recommendation.id,
        requirement_id=requirement_id_override or requirement.id,
        status=status, supporting_evidence="", notes="", matching_confidence=0.9,
    )
    db.add(row)
    db.commit()
    return row


def _make_gapful_mission(db, company, user, *, requirement_type, recommendation_type=RecommendationType.NO_GO, gap_count=1, overall_confidence=0.8, tender_name="T"):
    """A mission with `gap_count` distinct mandatory, NOT_MET requirements
    all of `requirement_type` -- used to prove a mission with several gaps
    of the same type still counts once toward the portfolio insight."""
    mission, tender = _seed_mission_with_tender(db, company, user, tender_name=tender_name)
    recommendation = _seed_recommendation(db, mission, recommendation_type=recommendation_type, overall_confidence=overall_confidence)
    for i in range(gap_count):
        requirement = _seed_requirement(db, tender, requirement_type=requirement_type, description=f"{requirement_type.value} req {i}")
        _seed_compliance_row(db, recommendation, requirement, status=MatchStatus.NOT_MET)
    return mission


def _make_clean_mission(db, company, user, *, recommendation_type=RecommendationType.GO, overall_confidence=0.9, tender_name="T"):
    mission, tender = _seed_mission_with_tender(db, company, user, tender_name=tender_name)
    recommendation = _seed_recommendation(db, mission, recommendation_type=recommendation_type, overall_confidence=overall_confidence)
    requirement = _seed_requirement(db, tender, requirement_type=RequirementType.ELIGIBILITY)
    _seed_compliance_row(db, recommendation, requirement, status=MatchStatus.MET)
    return mission


def _make_go_mission(db, company, user, *, overall_confidence=0.9, tender_name="T"):
    """Genuinely live-computes to GO: one MET mandatory CAPABILITY_CLAIM
    item, nothing else -- qualification PASS, readiness READY, no
    optional-issue overload."""
    return _make_clean_mission(db, company, user, overall_confidence=overall_confidence, tender_name=tender_name)


def _make_conditional_go_mission(db, company, user, *, overall_confidence=0.9, tender_name="T"):
    """Genuinely live-computes to CONDITIONAL_GO: a mandatory
    CAPABILITY_CLAIM item left REVIEW_REQUIRED -> compute_qualification()
    returns CONDITIONAL, which compute_recommendation_type() always maps
    to CONDITIONAL_GO regardless of readiness."""
    mission, tender = _seed_mission_with_tender(db, company, user, tender_name=tender_name)
    recommendation = _seed_recommendation(db, mission, overall_confidence=overall_confidence)
    requirement = _seed_requirement(db, tender, requirement_type=RequirementType.CERTIFICATION, mandatory=True)
    _seed_compliance_row(db, recommendation, requirement, status=MatchStatus.REVIEW_REQUIRED)
    return mission


def _make_review_mission(db, company, user, *, overall_confidence=0.9, tender_name="T"):
    """Genuinely live-computes to REVIEW: qualification PASS (one MET
    mandatory CAPABILITY_CLAIM item), readiness READY (no gating items
    at all), but 3 non-mandatory items in REVIEW_REQUIRED/CONDITIONAL/
    NOT_MET status -- exceeding settings.max_optional_review_items (2)."""
    mission, tender = _seed_mission_with_tender(db, company, user, tender_name=tender_name)
    recommendation = _seed_recommendation(db, mission, overall_confidence=overall_confidence)
    ok_requirement = _seed_requirement(db, tender, requirement_type=RequirementType.ELIGIBILITY, mandatory=True)
    _seed_compliance_row(db, recommendation, ok_requirement, status=MatchStatus.MET)
    for i, status in enumerate((MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL, MatchStatus.NOT_MET)):
        optional_requirement = _seed_requirement(
            db, tender, requirement_type=RequirementType.EXPERIENCE, mandatory=False, description=f"optional {i}"
        )
        _seed_compliance_row(db, recommendation, optional_requirement, status=status)
    return mission


def _make_no_go_mission(db, company, user, *, overall_confidence=0.9, tender_name="T"):
    """Genuinely live-computes to NO_GO: reuses _make_gapful_mission, a
    mandatory CAPABILITY_CLAIM item that is NOT_MET -> qualification FAIL."""
    return _make_gapful_mission(
        db, company, user, requirement_type=RequirementType.CERTIFICATION,
        overall_confidence=overall_confidence, tender_name=tender_name,
    )


def _get_portfolio(client, user):
    res = client.get("/api/v1/portfolio", headers=_auth_headers(user))
    assert res.status_code == 200, res.text
    return res.json()


# -- Distinct-mission counting (the critical aggregation rule) --------------


def test_five_missions_three_share_requirement_type(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    for _ in range(3):
        _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    for _ in range(2):
        _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 5
    assert data["insight"]["what"] == "3 of 5 active opportunities contain unmet certification-type requirements."
    assert len(data["insight"]["affected_mission_ids"]) == 3


def test_one_mission_with_multiple_gaps_counts_once(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # One mission, THREE certification-type gaps -- must count as 1, not 3.
    _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION, gap_count=3)
    _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 2
    assert data["insight"]["what"] == "1 of 2 active opportunities contain unmet certification-type requirements."
    assert len(data["insight"]["affected_mission_ids"]) == 1


def test_tied_requirement_types_use_combined_wording(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    for _ in range(2):
        _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    for _ in range(2):
        _make_gapful_mission(db, company, admin, requirement_type=RequirementType.EXPERIENCE)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 4
    # Deterministic ordering: sorted by enum value ("certification" < "experience").
    assert data["insight"]["what"] == "2 of 4 active opportunities contain unmet certification and experience requirements."
    assert set(data["insight"]["affected_requirement_types"]) == {"certification", "experience"}
    assert len(data["insight"]["affected_mission_ids"]) == 4


# -- Active-mission definition -----------------------------------------------


def test_archived_missions_excluded(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    active = _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    archived = _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    archived.status = MissionStatus.ARCHIVED
    db.commit()

    data = _get_portfolio(client, admin)
    all_mission_ids = {
        o["mission_id"] for bucket in ("prioritize", "review", "deprioritize") for o in data[bucket]
    }
    assert str(archived.id) not in all_mission_ids
    assert data["active_count"] == 1
    assert data["analyzed_count"] == 1
    assert data["insight"]["what"] == "1 of 1 active opportunities contain unmet certification-type requirements."


def test_zero_active_missions_empty_portfolio(client):
    db = _seeded_session(client)
    _company, admin = _seed_company_and_admin(db)

    data = _get_portfolio(client, admin)
    assert data["prioritize"] == data["review"] == data["deprioritize"] == []
    assert data["not_yet_analyzed"] == []
    assert data["unable_to_load"] == []
    assert data["insight"] is None
    assert data["analyzed_count"] == 0
    assert data["active_count"] == 0


def test_only_archived_missions_behaves_like_empty(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    m = _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    m.status = MissionStatus.ARCHIVED
    db.commit()

    data = _get_portfolio(client, admin)
    assert data["active_count"] == 0
    assert data["insight"] is None


# -- Not-yet-analyzed vs. unable-to-load isolation ---------------------------


def test_not_yet_analyzed_mission_is_excluded_from_buckets_and_insight(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # No Recommendation at all -- Mission.recommendation_id stays None.
    unanalyzed, _tender = _seed_mission_with_tender(db, company, admin, status=MissionStatus.CREATED)
    _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 1
    assert data["active_count"] == 2
    assert len(data["not_yet_analyzed"]) == 1
    assert data["not_yet_analyzed"][0]["mission_id"] == str(unanalyzed.id)
    not_yet_ids = {m["mission_id"] for m in data["not_yet_analyzed"]}
    bucket_ids = {o["mission_id"] for bucket in ("prioritize", "review", "deprioritize") for o in data[bucket]}
    assert not_yet_ids.isdisjoint(bucket_ids)


def test_incomplete_evaluation_isolated_without_crashing_portfolio(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # A Recommendation + ComplianceMatrix row whose requirement_id points
    # at a Requirement that does not exist -- get_evaluation_bundle's own
    # requirements_by_id lookup will miss it, so _build_response raises a
    # KeyError when assembling gap_analysis. This is the "unable to load"
    # path, not the "not yet analyzed" path -- exercised without mocking
    # anything, using a real data-integrity gap.
    broken, tender = _seed_mission_with_tender(db, company, admin)
    recommendation = _seed_recommendation(db, broken)
    _seed_compliance_row(db, recommendation, requirement=None, status=MatchStatus.NOT_MET, requirement_id_override=uuid.uuid4())

    healthy = _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert len(data["unable_to_load"]) == 1
    assert data["unable_to_load"][0]["mission_id"] == str(broken.id)
    # The healthy mission must still be present and correctly bucketed --
    # one broken mission must not take down the whole response.
    prioritize_ids = {o["mission_id"] for o in data["prioritize"]}
    assert str(healthy.id) in prioritize_ids
    assert data["analyzed_count"] == 1  # only the healthy mission


# -- Multi-tenancy ------------------------------------------------------------


def test_company_isolation(client):
    db = _seeded_session(client)
    company_a, admin_a = _seed_company_and_admin(db)
    company_b, admin_b = _seed_company_and_admin(db)
    mission_a = _make_gapful_mission(db, company_a, admin_a, requirement_type=RequirementType.CERTIFICATION)
    mission_b = _make_clean_mission(db, company_b, admin_b)

    data_a = _get_portfolio(client, admin_a)
    data_b = _get_portfolio(client, admin_b)

    a_ids = {o["mission_id"] for bucket in ("prioritize", "review", "deprioritize") for o in data_a[bucket]}
    b_ids = {o["mission_id"] for bucket in ("prioritize", "review", "deprioritize") for o in data_b[bucket]}
    assert str(mission_a.id) not in b_ids
    assert str(mission_b.id) not in a_ids
    assert data_a["analyzed_count"] == 1
    assert data_b["analyzed_count"] == 1


# -- Bucket mapping and confidence ordering ----------------------------------


def test_all_four_recommendation_types_map_to_expected_bucket(client):
    # Recommendation.recommendation_type is a persisted-history field only --
    # _build_response() always live-recomputes the actual value from real
    # compliance/requirement data (see backend/app/api/v1/evaluation.py). So
    # each of the four target types is produced here via real seeded data
    # known to live-compute to that type (see decision_engine.compute_recommendation_type),
    # not via the (ignored) recommendation_type persisted field.
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    go = _make_go_mission(db, company, admin, tender_name="GO")
    cgo = _make_conditional_go_mission(db, company, admin, tender_name="CGO")
    review = _make_review_mission(db, company, admin, tender_name="REVIEW")
    nogo = _make_no_go_mission(db, company, admin, tender_name="NOGO")

    data = _get_portfolio(client, admin)
    assert {o["mission_id"] for o in data["prioritize"]} == {str(go.id)}
    assert {o["mission_id"] for o in data["review"]} == {str(cgo.id), str(review.id)}
    assert {o["mission_id"] for o in data["deprioritize"]} == {str(nogo.id)}


def test_confidence_sorted_descending_within_bucket(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    _make_clean_mission(db, company, admin, recommendation_type=RecommendationType.GO, overall_confidence=0.6, tender_name="Low")
    _make_clean_mission(db, company, admin, recommendation_type=RecommendationType.GO, overall_confidence=0.95, tender_name="High")

    data = _get_portfolio(client, admin)
    confidences = [o["overall_confidence"] for o in data["prioritize"]]
    assert confidences == sorted(confidences, reverse=True)
    assert data["prioritize"][0]["tender_name"] == "High"


def test_go_never_ranks_below_no_go_regardless_of_confidence(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # Adversarial: a high-confidence NO_GO and a low-confidence GO. Both
    # seeded with real data that live-computes to the intended type (see
    # the comment on test_all_four_recommendation_types_map_to_expected_bucket).
    _make_no_go_mission(db, company, admin, overall_confidence=0.97, tender_name="ConfidentNoGo")
    _make_go_mission(db, company, admin, overall_confidence=0.51, tender_name="UnsureGo")

    data = _get_portfolio(client, admin)
    prioritize_names = {o["tender_name"] for o in data["prioritize"]}
    deprioritize_names = {o["tender_name"] for o in data["deprioritize"]}
    assert prioritize_names == {"UnsureGo"}
    assert deprioritize_names == {"ConfidentNoGo"}
    # Structural guarantee, not a confidence comparison: buckets are
    # disjoint, so a NO_GO can never appear in the same list as a GO no
    # matter what either mission's confidence is.


# -- Override semantics -------------------------------------------------------


def test_override_moves_bucket_but_not_structural_gap(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    mission, tender = _seed_mission_with_tender(db, company, admin)
    recommendation = _seed_recommendation(db, mission, recommendation_type=RecommendationType.NO_GO)
    requirement = _seed_requirement(db, tender, requirement_type=RequirementType.CERTIFICATION, mandatory=True)
    _seed_compliance_row(db, recommendation, requirement, status=MatchStatus.NOT_MET)

    data_before = _get_portfolio(client, admin)
    assert data_before["insight"]["what"] == "1 of 1 active opportunities contain unmet certification-type requirements."
    deprioritize_ids = {o["mission_id"] for o in data_before["deprioritize"]}
    assert str(mission.id) in deprioritize_ids

    override_res = client.post(
        f"/api/v1/missions/{mission.id}/requirements/{requirement.id}/override",
        json={"note": "Strategic partnership provides access to required capability."},
        headers=_auth_headers(admin),
    )
    assert override_res.status_code in (200, 201), override_res.text

    data_after = _get_portfolio(client, admin)
    # The mission's live bucket moves -- the only gap is now overridden,
    # so qualification is no longer blocked.
    prioritize_ids = {o["mission_id"] for o in data_after["prioritize"]}
    assert str(mission.id) in prioritize_ids
    deprioritize_ids_after = {o["mission_id"] for o in data_after["deprioritize"]}
    assert str(mission.id) not in deprioritize_ids_after
    # But the structural insight is UNCHANGED -- the underlying capability
    # gap does not disappear from portfolio intelligence just because one
    # mission accepted the risk. This is the one behavior the approved
    # plan singled out as most important to get right.
    assert data_after["insight"]["what"] == "1 of 1 active opportunities contain unmet certification-type requirements."
    assert data_after["insight"]["affected_mission_ids"] == [str(mission.id)]


# -- No LLM call --------------------------------------------------------------


def test_portfolio_never_calls_the_llm_client(client, monkeypatch):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    _make_clean_mission(db, company, admin)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("Portfolio must never call the LLM client.")

    monkeypatch.setattr(decision_engine, "get_llm_client", _fail_if_called)

    data = _get_portfolio(client, admin)  # would raise AssertionError above if an LLM call were attempted
    assert data["analyzed_count"] == 2
    # qualification_risk_exposure is computed in this same call -- proves
    # it never triggers a second, separate LLM-touching code path either.
    assert data["qualification_risk_exposure"] is not None


# -- No hard-coded insight numbers --------------------------------------------


def test_insight_numbers_reflect_actual_seeded_data_not_a_constant(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    for _ in range(4):
        _make_gapful_mission(db, company, admin, requirement_type=RequirementType.TECHNICAL)
    for _ in range(3):
        _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 7
    assert data["insight"]["what"] == "4 of 7 active opportunities contain unmet technical-type requirements."
    assert data["insight"]["now_what"] == "Addressing this would remove a current blocker from 4 of 7 active opportunities."


# -- Qualification Risk Exposure (second Portfolio insight) ------------------
# Approved scope: "{N} of {M} active opportunities currently carry at
# least one mandatory qualification gap." Distinct from the flagship
# insight (which names the single most common requirement TYPE) -- this
# counts every mission with ANY qualification gap, regardless of type.


def test_exposure_one_mission_multiple_gaps_counts_once(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # Two different gap TYPES on the same mission -- must still count as
    # exactly one affected opportunity for exposure purposes.
    mission, tender = _seed_mission_with_tender(db, company, admin)
    recommendation = _seed_recommendation(db, mission, recommendation_type=RecommendationType.NO_GO)
    cert_req = _seed_requirement(db, tender, requirement_type=RequirementType.CERTIFICATION, description="cert gap")
    _seed_compliance_row(db, recommendation, cert_req, status=MatchStatus.NOT_MET)
    fin_req = _seed_requirement(db, tender, requirement_type=RequirementType.EXPERIENCE, description="experience gap")
    _seed_compliance_row(db, recommendation, fin_req, status=MatchStatus.NOT_MET)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 1
    assert data["qualification_risk_exposure"]["what"] == (
        "1 of 1 active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_multiple_affected_missions(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    # 3 affected (different gap types, deliberately not all the same type
    # -- proves exposure is type-agnostic, unlike the flagship) out of 5
    # analyzed missions.
    _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    _make_gapful_mission(db, company, admin, requirement_type=RequirementType.EXPERIENCE)
    _make_gapful_mission(db, company, admin, requirement_type=RequirementType.TECHNICAL)
    for _ in range(2):
        _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 5
    assert data["qualification_risk_exposure"]["what"] == (
        "3 of 5 active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_zero_when_no_gaps_but_missions_analyzed(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    for _ in range(3):
        _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 3
    # Real zero, never hidden and never a "0 of 0".
    assert data["qualification_risk_exposure"]["what"] == (
        "0 of 3 active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_none_when_zero_analyzed_missions(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)  # no missions at all

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == 0
    assert data["qualification_risk_exposure"] is None


def test_exposure_survives_override_unchanged(client):
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    mission, tender = _seed_mission_with_tender(db, company, admin)
    recommendation = _seed_recommendation(db, mission, recommendation_type=RecommendationType.NO_GO)
    requirement = _seed_requirement(db, tender, requirement_type=RequirementType.CERTIFICATION, mandatory=True)
    _seed_compliance_row(db, recommendation, requirement, status=MatchStatus.NOT_MET)

    data_before = _get_portfolio(client, admin)
    assert data_before["qualification_risk_exposure"]["what"] == (
        "1 of 1 active opportunities currently carry at least one mandatory qualification gap."
    )
    assert str(mission.id) in {o["mission_id"] for o in data_before["deprioritize"]}

    override_res = client.post(
        f"/api/v1/missions/{mission.id}/requirements/{requirement.id}/override",
        json={"note": "Risk accepted for this specific bid."},
        headers=_auth_headers(admin),
    )
    assert override_res.status_code in (200, 201), override_res.text

    data_after = _get_portfolio(client, admin)
    # Live bucket moved (override resolves qualification for this mission)...
    assert str(mission.id) in {o["mission_id"] for o in data_after["prioritize"]}
    assert str(mission.id) not in {o["mission_id"] for o in data_after["deprioritize"]}
    # ...but exposure is UNCHANGED -- the override is bid-specific risk
    # acceptance, not proof the underlying capability gap disappeared.
    assert data_after["qualification_risk_exposure"]["what"] == (
        "1 of 1 active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_multi_tenant_isolation(client):
    db = _seeded_session(client)
    company_a, admin_a = _seed_company_and_admin(db)
    company_b, admin_b = _seed_company_and_admin(db)
    for _ in range(4):
        _make_gapful_mission(db, company_a, admin_a, requirement_type=RequirementType.CERTIFICATION)
    _make_clean_mission(db, company_b, admin_b)

    data_b = _get_portfolio(client, admin_b)
    # Company A's 4 affected missions must never leak into company B's
    # exposure count.
    assert data_b["analyzed_count"] == 1
    assert data_b["qualification_risk_exposure"]["what"] == (
        "0 of 1 active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_uses_dynamically_seeded_counts_not_hardcoded(client):
    """Seeds a variable, arbitrary-ish mix and asserts against counts
    DERIVED from what was actually seeded, not a hand-picked constant --
    proves the computation is real aggregation, not a lucky hard-coded match."""
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)

    gapful_types = [RequirementType.CERTIFICATION, RequirementType.TECHNICAL, RequirementType.EXPERIENCE,
                     RequirementType.CERTIFICATION, RequirementType.ELIGIBILITY]
    clean_count = 3
    for t in gapful_types:
        _make_gapful_mission(db, company, admin, requirement_type=t)
    for _ in range(clean_count):
        _make_clean_mission(db, company, admin)

    expected_n = len(gapful_types)  # each gapful mission is distinct, one gap type each
    expected_m = len(gapful_types) + clean_count

    data = _get_portfolio(client, admin)
    assert data["analyzed_count"] == expected_m
    assert data["qualification_risk_exposure"]["what"] == (
        f"{expected_n} of {expected_m} active opportunities currently carry at least one mandatory qualification gap."
    )


def test_exposure_does_not_change_existing_flagship_insight(client):
    """Regression guard: adding the second insight must not alter the
    flagship insight's text or affected_mission_ids in any way."""
    db = _seeded_session(client)
    company, admin = _seed_company_and_admin(db)
    for _ in range(3):
        _make_gapful_mission(db, company, admin, requirement_type=RequirementType.CERTIFICATION)
    for _ in range(2):
        _make_clean_mission(db, company, admin)

    data = _get_portfolio(client, admin)
    # Identical to test_five_missions_three_share_requirement_type's
    # assertions -- proves the flagship is byte-for-byte unchanged.
    assert data["insight"]["what"] == "3 of 5 active opportunities contain unmet certification-type requirements."
    assert len(data["insight"]["affected_mission_ids"]) == 3
    # And the second insight is present alongside it, independently correct.
    assert data["qualification_risk_exposure"]["what"] == (
        "3 of 5 active opportunities currently carry at least one mandatory qualification gap."
    )

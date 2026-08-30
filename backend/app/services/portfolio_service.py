"""
Portfolio aggregation — read-only, company-scoped.

Deliberately thin: this module owns grouping/insight logic only. It never
re-implements qualification, risk, recommendation, or confidence rules —
every mission's live recommendation/qualification state is obtained by
calling the exact same functions the existing GET /evaluation/{mission_id}
route already calls (decision_service.get_evaluation_bundle +
app.api.v1.evaluation._build_response), so Portfolio can never drift from
what a user sees on drill-in. See docs/... implementation plan, "Portfolio
Data Model / Query Strategy" for the approved shape this follows.

Reusing `_build_response` from the API layer (rather than the service
layer) is a deliberate, minimal choice: that function is already a plain,
standalone, importable module-level function — not nested in a route
closure — so reusing it costs a zero-line change to evaluation.py. The
alternative (extracting/moving it into decision_service.py) would touch a
file two existing, tested routes depend on for no behavioral gain; this
avoids that risk entirely. The one trade-off: this file imports across the
conventional services->api dependency direction. Flagged here deliberately
rather than silently done.

No new table, no new persisted state, no LLM call, no mutation of Mission/
Recommendation/ComplianceMatrix — verified true for every function below by
construction (every function is either a plain read or pure computation).
"""

import logging
import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.api.v1.evaluation import _build_response  # noqa: reuse, not duplication — see module docstring
from app.models import Document, Mission, Tender
from app.models.enums import MissionStatus, RecommendationType, RequirementType
from app.schemas.portfolio import (
    NotYetAnalyzedMission,
    OpportunitySummary,
    PortfolioInsight,
    PortfolioResponse,
    QualificationRiskExposure,
    UnableToLoadMission,
)
from app.services import decision_service, mission_service
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Presentation-only grouping over the existing RecommendationType values —
# does not modify or extend that enum. CONDITIONAL_GO and REVIEW share a
# bucket because both mean "not a clean go, not a clean no-go" from a
# resourcing standpoint; GO and NO_GO are never in the same bucket as each
# other or as anything else, so a NO_GO can never appear ahead of a GO
# regardless of confidence — that guarantee comes from this mapping being
# applied before any confidence-based sort, not from a confidence rule.
_BUCKET_BY_RECOMMENDATION: dict[RecommendationType, str] = {
    RecommendationType.GO: "prioritize",
    RecommendationType.CONDITIONAL_GO: "review",
    RecommendationType.REVIEW: "review",
    RecommendationType.NO_GO: "deprioritize",
}


def _active_missions(db: Session, company_id: uuid.UUID) -> list[Mission]:
    """'Active' = every Mission except ARCHIVED — the exact, already-shipped
    convention Dashboard.tsx uses (`m.status !== "archived"`), not a new
    Portfolio-specific definition. See implementation plan §7."""
    missions = mission_service.list_missions(db, company_id)
    return [m for m in missions if m.status != MissionStatus.ARCHIVED]


def _tender_names(db: Session, missions: list[Mission]) -> dict[uuid.UUID, str | None]:
    """One batched query for tender display names, keyed by mission_id —
    same N+1-avoidance shape as missions.py::_attach_tender_info, kept as a
    small local helper here rather than importing that function, since it
    returns a full MissionRead (more than Portfolio needs) and is itself a
    private, route-local helper. This mirrors its pattern; it does not
    duplicate any decision/qualification logic (a name lookup is not
    decision logic)."""
    if not missions:
        return {}
    mission_ids = [m.id for m in missions]
    tenders = db.query(Tender).filter(Tender.mission_id.in_(mission_ids)).all()
    tender_by_mission = {t.mission_id: t for t in tenders}
    doc_ids = [t.uploaded_document for t in tenders if t.uploaded_document]
    doc_by_id = {}
    if doc_ids:
        doc_by_id = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
    names: dict[uuid.UUID, str | None] = {}
    for m in missions:
        tender = tender_by_mission.get(m.id)
        if tender is None:
            names[m.id] = None
            continue
        document = doc_by_id.get(tender.uploaded_document) if tender.uploaded_document else None
        names[m.id] = tender.tender_name or (document.file_name if document else None)
    return names


def _build_insight(
    type_to_missions: dict[RequirementType, set[uuid.UUID]], analyzed_count: int
) -> PortfolioInsight | None:
    """
    Deterministic, template-only — no LLM call anywhere in this function.

    `type_to_missions[t]` is the SET of distinct mission ids where `t`
    appears as a mandatory, NOT_MET requirement type (i.e. a genuine
    qualification gap) — built by the caller from each analyzed mission's
    `remediation_summary.qualification_gaps`, deduplicated to a set per
    mission before this function ever sees it, so a mission with three
    certification gaps has already been reduced to one membership. This
    function only picks the leading type(s) and renders the sentence; it
    does not itself dedupe missions (that already happened) and it never
    re-derives qualification from raw ComplianceMatrix rows.

    Ties (multiple requirement types affecting the same maximum number of
    missions) are combined into one sentence naming every leading type,
    never resolved by an arbitrary pick — approved plan §10 (Version C:
    "Certification and Experience requirements are currently tied...").

    Wording is deliberately conditional/factual only — "would remove a
    current blocker from N of M", never "will unlock" or any guaranteed-
    outcome phrasing (approved plan §13).
    """
    if not type_to_missions or analyzed_count == 0:
        return None

    max_count = max(len(missions) for missions in type_to_missions.values())
    if max_count == 0:
        return None

    leading_types = sorted(
        (t for t, missions in type_to_missions.items() if len(missions) == max_count),
        key=lambda t: t.value,
    )
    labels = [t.value.replace("_", " ") for t in leading_types]
    affected_mission_ids = sorted(
        {mid for t in leading_types for mid in type_to_missions[t]}, key=str
    )
    n = max_count
    m = analyzed_count

    if len(labels) == 1:
        label = labels[0]
        what = f"{n} of {m} active opportunities contain unmet {label}-type requirements."
        why = (
            f"{label.capitalize()} requirements are currently the most common qualification "
            "blocker across your active opportunities."
        )
    else:
        joined = " and ".join(labels)
        what = f"{n} of {m} active opportunities contain unmet {joined} requirements."
        why = (
            f"{joined.capitalize()} requirements are currently tied as the most common "
            "qualification blockers across your active opportunities."
        )

    now_what = f"Addressing this would remove a current blocker from {n} of {m} active opportunities."

    return PortfolioInsight(
        what=what,
        why=why,
        now_what=now_what,
        affected_requirement_types=leading_types,
        affected_mission_ids=affected_mission_ids,
    )


def _build_qualification_risk_exposure(
    type_to_missions: dict[RequirementType, set[uuid.UUID]], analyzed_count: int
) -> QualificationRiskExposure | None:
    """
    Second Portfolio insight (approved: Qualification Risk Exposure) --
    HOW MANY active opportunities are affected by any mandatory
    qualification gap, independent of which requirement type. Deliberately
    reuses `type_to_missions` -- the exact same per-mission
    qualification_gaps membership data _build_insight() above already
    derives, no new query, no new per-mission loop, no re-derivation of
    qualification. A mission's membership in `type_to_missions` (any type)
    means remediation_summary.qualification_gaps was non-empty for it,
    which classify_remediation() guarantees stays true regardless of
    QualificationOverride -- so this count is override-independent by
    construction, exactly like the flagship insight's affected_mission_ids.

    Unlike _build_insight(), this returns a result whenever analyzed_count
    > 0 -- including the honest n=0 case ("no active opportunity currently
    carries a qualification gap"), which must never be hidden. None only
    when there are zero analyzed active missions.
    """
    if analyzed_count == 0:
        return None

    affected_mission_ids: set[uuid.UUID] = set()
    for missions in type_to_missions.values():
        affected_mission_ids |= missions

    n = len(affected_mission_ids)
    m = analyzed_count
    what = f"{n} of {m} active opportunities currently carry at least one mandatory qualification gap."
    return QualificationRiskExposure(what=what)


def get_portfolio(db: Session, company_id: uuid.UUID) -> PortfolioResponse:
    """
    Live, read-only, company-scoped. Nothing here is persisted, cached, or
    materialized — every call re-derives the response from current Mission/
    Recommendation/ComplianceMatrix rows (approved plan §15).

    company_id must come from the authenticated request context in the
    caller (see api/v1/portfolio.py) — this function never accepts or
    infers a company_id from anything else, and every downstream call
    (mission_service.list_missions, decision_service.get_evaluation_bundle)
    is itself company-scoped, so isolation is enforced at every layer, not
    just here.
    """
    missions = _active_missions(db, company_id)
    tender_names = _tender_names(db, missions)

    prioritize: list[OpportunitySummary] = []
    review: list[OpportunitySummary] = []
    deprioritize: list[OpportunitySummary] = []
    not_yet_analyzed: list[NotYetAnalyzedMission] = []
    unable_to_load: list[UnableToLoadMission] = []
    type_to_missions: dict[RequirementType, set[uuid.UUID]] = defaultdict(set)
    analyzed_count = 0

    for mission in missions:
        try:
            recommendation, compliance_rows, requirements_by_id = decision_service.get_evaluation_bundle(
                db, mission.id, company_id
            )
        except NotFoundError:
            # Mission.recommendation_id is None — genuinely not yet
            # analyzed, not an error. Never treated as a "gap".
            not_yet_analyzed.append(
                NotYetAnalyzedMission(mission_id=mission.id, tender_name=tender_names.get(mission.id), status=mission.status)
            )
            continue

        try:
            evaluation = _build_response(db, recommendation, compliance_rows, requirements_by_id)
        except Exception:
            # Isolate one mission's failure from the rest of the portfolio
            # (approved plan §14/§17) -- logged, never silently dropped,
            # never given a fabricated recommendation.
            logger.warning(
                "Portfolio: could not build evaluation response for mission %s (company %s) -- excluded from aggregation.",
                mission.id,
                company_id,
                exc_info=True,
            )
            unable_to_load.append(
                UnableToLoadMission(mission_id=mission.id, tender_name=tender_names.get(mission.id))
            )
            continue

        analyzed_count += 1
        summary = OpportunitySummary(
            mission_id=mission.id,
            tender_name=tender_names.get(mission.id),
            recommendation_type=evaluation.recommendation.recommendation_type,
            overall_confidence=evaluation.recommendation.overall_confidence,
        )
        bucket_name = _BUCKET_BY_RECOMMENDATION[evaluation.recommendation.recommendation_type]
        {"prioritize": prioritize, "review": review, "deprioritize": deprioritize}[bucket_name].append(summary)

        # Structural gap signal for the insight -- read from
        # remediation_summary.qualification_gaps, which classify_remediation()
        # guarantees stays populated regardless of QualificationOverride
        # (an overridden item is never removed from this bucket, only
        # flagged `overridden=true`). This is exactly why the insight below
        # cannot be accidentally derived from the live, override-aware
        # recommendation_type -- it is read from a different, override-
        # independent field entirely. See approved plan §5/"Override Rule".
        gap_types = {g.requirement_type for g in evaluation.remediation_summary.qualification_gaps}
        for t in gap_types:
            type_to_missions[t].add(mission.id)

    for bucket in (prioritize, review, deprioritize):
        bucket.sort(key=lambda o: (o.overall_confidence is None, -(o.overall_confidence or 0.0)))

    insight = _build_insight(type_to_missions, analyzed_count)
    qualification_risk_exposure = _build_qualification_risk_exposure(type_to_missions, analyzed_count)

    return PortfolioResponse(
        prioritize=prioritize,
        review=review,
        deprioritize=deprioritize,
        not_yet_analyzed=not_yet_analyzed,
        unable_to_load=unable_to_load,
        insight=insight,
        qualification_risk_exposure=qualification_risk_exposure,
        analyzed_count=analyzed_count,
        active_count=len(missions),
    )

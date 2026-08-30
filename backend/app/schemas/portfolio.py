"""
Portfolio aggregation — response contracts.

Read-only, presentation-layer types over data the Decision Engine and
Evaluation response already produce (RecommendationType, overall_confidence,
RemediationSummary.qualification_gaps). No new persisted concept here —
mirrors GapAnalysisEntry's own "Computed at response time... not a stored
table" precedent in app/schemas/decision.py.
"""

import uuid

from pydantic import BaseModel

from app.models.enums import MissionStatus, RecommendationType, RequirementType


class OpportunitySummary(BaseModel):
    """One active, already-analyzed Mission as it appears in a Portfolio bucket.
    `recommendation_type` is the LIVE-recomputed value (same one GET
    /evaluation/{mission_id} returns, override-aware) -- see
    portfolio_service.get_portfolio()'s module docstring for why this is
    deliberately different from the requirement_type set used to build the
    insight below."""

    mission_id: uuid.UUID
    tender_name: str | None
    recommendation_type: RecommendationType
    overall_confidence: float | None


class NotYetAnalyzedMission(BaseModel):
    """An active Mission with no Recommendation yet (Mission.recommendation_id
    is None) -- distinct from a bucketed opportunity, never silently folded
    into one. See decision_service.get_evaluation()'s NotFoundError, which is
    exactly what signals this state."""

    mission_id: uuid.UUID
    tender_name: str | None
    status: MissionStatus


class UnableToLoadMission(BaseModel):
    """An active Mission whose evaluation bundle could not be assembled this
    request (an unexpected exception was raised and caught) -- isolated so
    one broken mission never fails the whole Portfolio response. Logged
    server-side; never silently dropped from the response, and never given
    a fabricated recommendation/confidence."""

    mission_id: uuid.UUID
    tender_name: str | None


class PortfolioInsight(BaseModel):
    """The flagship deterministic insight (Version A: requirement-type-level).
    `what`/`why`/`now_what` are plain factual sentences, never a guaranteed-
    outcome claim -- see portfolio_service._build_insight()'s docstring.
    `affected_mission_ids` is the union of missions behind whichever
    requirement type(s) are named in the sentence (more than one only when
    there is a genuine tie -- see _build_insight())."""

    what: str
    why: str
    now_what: str
    affected_requirement_types: list[RequirementType]
    affected_mission_ids: list[uuid.UUID]


class QualificationRiskExposure(BaseModel):
    """Second Portfolio insight (approved: Qualification Risk Exposure) --
    HOW MANY active opportunities are affected by any mandatory
    qualification gap, as opposed to the flagship PortfolioInsight's WHAT
    requirement-type is most commonly the blocker. Deliberately minimal:
    a single deterministic factual sentence, no why/now_what -- that is
    the entire approved scope for this insight.

    Counts a mission if remediation_summary.qualification_gaps is
    non-empty, REGARDLESS of whether one or more of those gaps have since
    been overridden -- classify_remediation() guarantees an overridden
    item stays in this bucket (only flagged `overridden=true`, never
    removed), so an administrator override changes a mission's live
    recommendation/bucket but never removes it from this exposure count.
    An override is bid-specific risk acceptance, not proof the underlying
    company capability gap disappeared.

    Present whenever analyzed_count > 0 (even n=0, which is a real,
    honest "no exposure" result and must never be hidden) -- None only
    when there are zero analyzed active missions, mirroring
    PortfolioResponse.insight's own empty-state rule."""

    what: str


class PortfolioResponse(BaseModel):
    prioritize: list[OpportunitySummary]
    review: list[OpportunitySummary]
    deprioritize: list[OpportunitySummary]
    not_yet_analyzed: list[NotYetAnalyzedMission]
    unable_to_load: list[UnableToLoadMission]
    # None only when there are zero analyzed missions with at least one
    # qualification gap between them -- an empty portfolio or an all-clean
    # portfolio both produce no insight, never a fabricated "0 of 0" sentence.
    insight: PortfolioInsight | None
    # Second, deliberately minimal insight -- see QualificationRiskExposure's
    # own docstring. None only when analyzed_count == 0 (same empty-state
    # rule as `insight` above); otherwise always present, including the
    # honest n=0 case.
    qualification_risk_exposure: QualificationRiskExposure | None
    # Denominator context for the UI -- how many active missions actually
    # have a completed evaluation (the `M` in "N of M"), distinct from
    # len(prioritize)+len(review)+len(deprioritize)+len(not_yet_analyzed)
    # only because unable_to_load missions are active but contribute to
    # neither count.
    analyzed_count: int
    active_count: int

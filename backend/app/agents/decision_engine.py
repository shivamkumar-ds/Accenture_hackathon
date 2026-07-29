"""
Decision Intelligence Engine — reasoning only, no persistence (that's
decision_service.py's job, same AI Service Layer / Business Logic Layer
split M3 and M5 already established).

Only one LLM call type exists in this whole module: per-requirement
matching. Everything else — recommendation type, risk level, required
verification, confidence propagation, the executive summary — is
deterministic computation over already-decided facts, per the
milestone's own instruction to avoid black-box behaviour wherever
possible.
"""

import uuid
from dataclasses import dataclass

from app.agents.json_utils import parse_json_response
from app.agents.llm_client import get_llm_client
from app.agents.prompts import decision_matching
from app.core.config import get_settings
from app.models.enums import CapabilityEntityType, MatchStatus, RecommendationType, RequirementType, RiskLevel
from app.schemas.extraction import DecisionMatchExtraction
from app.services.freshness import evaluate_freshness

settings = get_settings()

# Which capability domains are actually candidates for each matchable
# requirement category. Deadline/EvaluationCriteria/Submission are
# deliberately absent — see PROCEDURAL_CATEGORIES below.
CATEGORY_DOMAINS: dict[RequirementType, list[CapabilityEntityType]] = {
    RequirementType.CERTIFICATION: [CapabilityEntityType.CERTIFICATION],
    RequirementType.EXPERIENCE: [CapabilityEntityType.PROJECT],
    RequirementType.ELIGIBILITY: [
        CapabilityEntityType.CERTIFICATION,
        CapabilityEntityType.FINANCIAL_RECORD,
        CapabilityEntityType.PROJECT,
    ],
    RequirementType.TECHNICAL: [
        CapabilityEntityType.EQUIPMENT,
        CapabilityEntityType.EMPLOYEE,
        CapabilityEntityType.PROJECT,
    ],
}

# These three are procedural facts about the tender process itself, not
# claims about company capability — no capability entity could
# "satisfy" a deadline. They skip matching entirely (see
# build_procedural_result below).
PROCEDURAL_CATEGORIES = {
    RequirementType.DEADLINE,
    RequirementType.EVALUATION_CRITERIA,
    RequirementType.SUBMISSION,
}


@dataclass
class MatchResult:
    requirement_id: uuid.UUID
    requirement_type: RequirementType
    mandatory: bool
    status: MatchStatus
    matched_entity_type: CapabilityEntityType | None
    matched_entity_id: uuid.UUID | None
    matching_confidence: float
    supporting_evidence: str
    notes: str


def _summarize_entity(entity_type: CapabilityEntityType, entity) -> str:
    if entity_type == CapabilityEntityType.CERTIFICATION:
        return f"Certification: {entity.certification_name}, issued by {entity.issuing_authority}, expires {entity.expiry_date}"
    if entity_type == CapabilityEntityType.EMPLOYEE:
        return f"Employee: {entity.name}, {entity.position}, qualification: {entity.qualification}, skills: {entity.skills}"
    if entity_type == CapabilityEntityType.PROJECT:
        return f"Project: client {entity.client}, industry {entity.industry}, value {entity.contract_value}, status {entity.completion_status}"
    if entity_type == CapabilityEntityType.EQUIPMENT:
        return f"Equipment: {entity.equipment_name}, category {entity.category}, quantity {entity.quantity}"
    if entity_type == CapabilityEntityType.FINANCIAL_RECORD:
        return f"Financial record: year {entity.financial_year}, revenue {entity.revenue}, net worth {entity.net_worth}"
    return "Unknown entity type"


def build_procedural_result(requirement) -> MatchResult:
    """Deadline/Evaluation Criteria/Submission — always REVIEW_REQUIRED, never matched against capability."""
    return MatchResult(
        requirement_id=requirement.id,
        requirement_type=requirement.requirement_type,
        mandatory=requirement.mandatory,
        status=MatchStatus.REVIEW_REQUIRED,
        matched_entity_type=None,
        matched_entity_id=None,
        matching_confidence=1.0,  # fully confident this classification itself is correct
        supporting_evidence="No company capability applies — this is a procedural tender requirement.",
        notes=(
            "This requirement is procedural (deadline, evaluation criteria, or submission "
            "format), not a claim about company capability. It cannot be automatically "
            "matched and always requires human review."
        ),
    )


async def match_requirement(
    requirement, candidates: list[tuple[CapabilityEntityType, object]], provider: str | None = None
) -> MatchResult:
    if requirement.requirement_type in PROCEDURAL_CATEGORIES:
        return build_procedural_result(requirement)

    if not candidates:
        domains = ", ".join(d.value for d in CATEGORY_DOMAINS[requirement.requirement_type])
        return MatchResult(
            requirement_id=requirement.id,
            requirement_type=requirement.requirement_type,
            mandatory=requirement.mandatory,
            status=MatchStatus.NOT_MET,
            matched_entity_type=None,
            matched_entity_id=None,
            matching_confidence=0.9,  # a "zero rows exist" finding is a DB fact, not a guess
            supporting_evidence=f"No records found in company capability graph for domain(s): {domains}.",
            notes="Deterministic: zero candidate entities exist in the relevant capability domain(s).",
        )

    candidate_summaries = [_summarize_entity(entity_type, entity) for entity_type, entity in candidates]
    client = get_llm_client(provider)
    raw_response = await client.complete(
        decision_matching.SYSTEM_PROMPT,
        decision_matching.build_prompt(requirement.description or "", candidate_summaries),
        purpose="decision_matching",
    )
    validated = DecisionMatchExtraction.model_validate(parse_json_response(raw_response))
    status = MatchStatus(validated.status)

    matched_entity_type = matched_entity_id = None
    matched_entity = None
    matching_confidence = 0.7  # a judgment call was made despite candidates existing
    supporting_evidence = f"No specific record matched among {len(candidates)} candidate(s) considered."

    if validated.matched_entity_index is not None and 0 <= validated.matched_entity_index < len(candidates):
        matched_entity_type, matched_entity = candidates[validated.matched_entity_index]
        matched_entity_id = matched_entity.id
        matching_confidence = float(matched_entity.confidence_score or 0.7)
        supporting_evidence = _summarize_entity(matched_entity_type, matched_entity)

    notes = validated.reasoning or "(no reasoning provided)"

    # Deterministic freshness override — only applies when a specific
    # entity was actually cited. Refinement: expired forces NOT_MET;
    # stale only downgrades MET to REVIEW_REQUIRED (never NOT_MET) —
    # the system never rejects a company solely for stale evidence.
    if matched_entity is not None:
        freshness = evaluate_freshness(matched_entity)
        if freshness["is_expired"]:
            status = MatchStatus.NOT_MET
            notes += " | OVERRIDE: cited evidence is expired — forced to NOT_MET."
        elif freshness["is_stale"] and status == MatchStatus.MET:
            status = MatchStatus.REVIEW_REQUIRED
            notes += (
                " | OVERRIDE: cited evidence is stale (beyond the configured staleness "
                "threshold) — downgraded from MET to REVIEW_REQUIRED, not rejected. "
                "Stale information is uncertain, not necessarily invalid."
            )
        elif freshness["is_stale"] and status == MatchStatus.CONDITIONAL:
            notes += " | Note: cited evidence is also stale; already conditional, no further downgrade applied."

    return MatchResult(
        requirement_id=requirement.id,
        requirement_type=requirement.requirement_type,
        mandatory=requirement.mandatory,
        status=status,
        matched_entity_type=matched_entity_type,
        matched_entity_id=matched_entity_id,
        matching_confidence=matching_confidence,
        supporting_evidence=supporting_evidence,
        notes=notes,
    )


def compute_risk_level(mandatory: bool, status: MatchStatus) -> RiskLevel:
    if mandatory and status == MatchStatus.NOT_MET:
        return RiskLevel.CRITICAL
    if mandatory and status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL):
        return RiskLevel.HIGH
    if status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL):
        return RiskLevel.MEDIUM
    if not mandatory and status == MatchStatus.NOT_MET:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def compute_requires_verification(
    mandatory: bool, status: MatchStatus, matching_confidence: float
) -> tuple[bool, str]:
    reasons = []
    if mandatory and status != MatchStatus.MET:
        reasons.append(f"Mandatory requirement with status '{status.value}'.")
    if status == MatchStatus.REVIEW_REQUIRED:
        reasons.append("Status is REVIEW_REQUIRED.")
    if matching_confidence < 0.7:
        reasons.append(f"Matching confidence ({matching_confidence}) is below the 0.7 threshold.")
    return (bool(reasons), " ".join(reasons) if reasons else "")


def compute_recommendation_type(results: list[MatchResult]) -> RecommendationType:
    if any(r.mandatory and r.status == MatchStatus.NOT_MET for r in results):
        return RecommendationType.NO_GO
    if any(r.mandatory and r.status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL) for r in results):
        return RecommendationType.CONDITIONAL_GO
    optional_issues = sum(
        1
        for r in results
        if not r.mandatory and r.status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL, MatchStatus.NOT_MET)
    )
    if optional_issues > settings.max_optional_review_items:
        return RecommendationType.REVIEW
    return RecommendationType.GO


# One severity scale drives both the recommendation and its risk level —
# avoids two separate, potentially inconsistent severity computations.
RECOMMENDATION_RISK_MAP = {
    RecommendationType.NO_GO: RiskLevel.CRITICAL,
    RecommendationType.CONDITIONAL_GO: RiskLevel.HIGH,
    RecommendationType.REVIEW: RiskLevel.MEDIUM,
    RecommendationType.GO: RiskLevel.LOW,
}


def compute_confidence_propagation(
    results: list[MatchResult], entity_confidences: list[float], document_confidences: list[float]
) -> dict:
    """
    Weighted, not a simple average — matching_confidence carries the
    highest weight (0.50) since it represents the engine's core
    reasoning. Capped so one genuinely weak stage can't be hidden by
    averaging with several strong ones: overall can never exceed the
    lowest individual stage by more than 0.15.
    """
    matching_values = [r.matching_confidence for r in results] or [0.5]
    matching_confidence = round(sum(matching_values) / len(matching_values), 4)
    entity_confidence = round(sum(entity_confidences) / len(entity_confidences), 4) if entity_confidences else 0.5
    document_confidence = (
        round(sum(document_confidences) / len(document_confidences), 4) if document_confidences else 0.5
    )

    non_clean = sum(1 for r in results if r.status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL))
    recommendation_confidence = round(1.0 - 0.5 * (non_clean / len(results)), 4) if results else 0.5

    stages = {
        "document_confidence": document_confidence,
        "entity_confidence": entity_confidence,
        "matching_confidence": matching_confidence,
        "recommendation_confidence": recommendation_confidence,
    }
    weights = {
        "document_confidence": 0.15,
        "entity_confidence": 0.15,
        "matching_confidence": 0.50,
        "recommendation_confidence": 0.20,
    }
    weighted_average = sum(stages[k] * weights[k] for k in stages)
    lowest_stage = min(stages.values())
    overall_confidence = round(min(weighted_average, lowest_stage + 0.15), 4)

    return {**stages, "overall_confidence": overall_confidence}


def build_executive_summary(
    recommendation_type: RecommendationType, results: list[MatchResult], confidence: dict
) -> str:
    """Deterministic string template, not an LLM call — see the strategy note on why."""
    total = len(results)
    met = sum(1 for r in results if r.status == MatchStatus.MET)
    not_met = sum(1 for r in results if r.status == MatchStatus.NOT_MET)
    review = sum(1 for r in results if r.status == MatchStatus.REVIEW_REQUIRED)
    conditional = sum(1 for r in results if r.status == MatchStatus.CONDITIONAL)
    mandatory_not_met = sum(1 for r in results if r.mandatory and r.status == MatchStatus.NOT_MET)

    return (
        f"Recommendation: {recommendation_type.value.upper().replace('_', ' ')}. "
        f"Evaluated {total} tender requirement(s): {met} met, {not_met} not met, "
        f"{review} requiring review, {conditional} conditionally met. "
        f"{mandatory_not_met} mandatory requirement(s) are not met. "
        f"Overall confidence: {confidence['overall_confidence']}. "
        f"See the Compliance Matrix for the complete per-requirement evidence and reasoning "
        f"behind this recommendation."
    )

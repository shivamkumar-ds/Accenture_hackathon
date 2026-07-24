"""
Event-Driven Revalidation Engine (M9).

Dependency-driven, not scan-driven: affected missions are found by
traversing CapabilityMapping -> ComplianceMatrix -> Recommendation ->
Mission, starting from the specific entity that changed — never by
iterating every Recommendation in the company.

Reuses, never duplicates: decision_service.run_evaluation() (M6) does
every bit of actual reasoning; this module only decides WHICH missions
need it and coalesces multiple triggers into one call per mission.

History is never touched. For a mission still AWAITING_APPROVAL,
re-evaluation behaves exactly as it already did in M6/M7 (repoints
Mission at the new Recommendation — nothing has been decided yet, so
there's no historical decision to protect). For a mission already
COMPLETED, run_evaluation() is called with preserve_mission_state=True:
a new Recommendation/CapabilitySnapshot/ComplianceMatrix genuinely
exist, for current operational awareness, but Mission.status,
Mission.recommendation_id, the original Recommendation, its
ComplianceMatrix rows, and the human's decision in AuditLog are all
completely untouched. ARCHIVED missions are skipped entirely.
"""

import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog, CapabilityMapping, ComplianceMatrix, Mission, Recommendation
from app.models.enums import CapabilityEntityType, MatchStatus, MissionStatus
from app.services import capability_service, decision_service, mission_service
from app.services.exceptions import ConflictError, ExtractionError, NotFoundError
from app.services.freshness import evaluate_freshness

REVALIDATION_AGENT = "revalidation_engine"


def _log(db: Session, mission_id: uuid.UUID, event: str, result: str = "") -> None:
    db.add(AuditLog(mission_id=mission_id, user_id=None, agent=REVALIDATION_AGENT, event=event, result=result))
    db.commit()


def find_affected_missions(
    db: Session, entity_type: CapabilityEntityType, entity_id: uuid.UUID, company_id: uuid.UUID
) -> set[uuid.UUID]:
    """
    Dependency traversal, exactly as required: CapabilityMapping (which
    entity was cited) -> ComplianceMatrix.evidence_reference -> Recommendation
    -> Mission. Never scans every Recommendation.

    Filters to missions whose CURRENT (latest, by generated_at) Recommendation
    still actually cites this entity — a historical, superseded Recommendation
    citing it doesn't count, since a newer evaluation may have already moved on.
    """
    mapping_ids = [
        row.id
        for row in db.query(CapabilityMapping.id)
        .filter(
            CapabilityMapping.capability_entity_type == entity_type,
            CapabilityMapping.capability_entity_id == entity_id,
        )
        .all()
    ]
    if not mapping_ids:
        return set()

    candidate_recommendation_ids = {
        row.recommendation_id
        for row in db.query(ComplianceMatrix.recommendation_id)
        .filter(ComplianceMatrix.evidence_reference.in_(mapping_ids))
        .distinct()
        .all()
    }
    if not candidate_recommendation_ids:
        return set()

    candidate_missions: dict[uuid.UUID, uuid.UUID] = {}
    for rec_id in candidate_recommendation_ids:
        recommendation = db.get(Recommendation, rec_id)
        mission = db.get(Mission, recommendation.mission_id)
        if mission is not None and mission.company_id == company_id and mission.status != MissionStatus.ARCHIVED:
            candidate_missions[mission.id] = rec_id

    affected: set[uuid.UUID] = set()
    for mission_id in candidate_missions:
        latest = decision_service.get_latest_recommendation_for_mission(db, mission_id)
        if latest is None:
            continue
        still_cited = (
            db.query(ComplianceMatrix)
            .join(CapabilityMapping, ComplianceMatrix.evidence_reference == CapabilityMapping.id)
            .filter(
                ComplianceMatrix.recommendation_id == latest.id,
                CapabilityMapping.capability_entity_type == entity_type,
                CapabilityMapping.capability_entity_id == entity_id,
            )
            .first()
        )
        if still_cited is not None:
            affected.add(mission_id)
    return affected


async def revalidate_missions(
    db: Session, mission_ids: set[uuid.UUID], company_id: uuid.UUID, reason: str
) -> list[Recommendation]:
    """
    One call per mission, regardless of how many entities/changes led to
    it being in mission_ids (the caller already coalesced to a set) —
    this is what guarantees at most one new Recommendation per mission
    per revalidation run.
    """
    new_recommendations = []
    for mission_id in mission_ids:
        mission = mission_service.get_mission(db, mission_id, company_id)
        if mission.status == MissionStatus.ARCHIVED:
            continue

        preserve = mission.status == MissionStatus.COMPLETED
        try:
            recommendation = await decision_service.run_evaluation(
                db, mission_id, company_id, preserve_mission_state=preserve
            )
        except ExtractionError as exc:
            _log(db, mission_id, "Revalidation failed", f"{reason} | {exc}")
            continue

        note = reason + (
            " (informational only — mission already decided; historical decision unchanged)"
            if preserve
            else ""
        )
        _log(db, mission_id, "Revalidation produced a new Recommendation", note)
        new_recommendations.append(recommendation)
    return new_recommendations


def _freshness_already_reflected(
    db: Session, recommendation_id: uuid.UUID, entity_type: CapabilityEntityType, entity_id: uuid.UUID, freshness: dict
) -> bool:
    """
    The actual idempotency mechanism for freshness-triggered revalidation.

    Checking row.status alone is NOT enough — caught via real testing: a
    row can be CONDITIONAL for reasons entirely unrelated to freshness
    (the mock's general humility about ambiguous technical/eligibility
    matches), which would false-positive as "already reflected" and
    silently skip a mission that genuinely needs revalidation. Requiring
    the specific override marker text decision_engine.py itself writes
    when it actually applies a freshness override disambiguates real
    cause from coincidental status, while still being a deterministic
    check against text the code controls, not fuzzy human-authored prose.
    """
    row = (
        db.query(ComplianceMatrix)
        .join(CapabilityMapping, ComplianceMatrix.evidence_reference == CapabilityMapping.id)
        .filter(
            ComplianceMatrix.recommendation_id == recommendation_id,
            CapabilityMapping.capability_entity_type == entity_type,
            CapabilityMapping.capability_entity_id == entity_id,
        )
        .first()
    )
    if row is None:
        return True
    notes = (row.notes or "").lower()
    if freshness["is_expired"]:
        return row.status == MatchStatus.NOT_MET and "cited evidence is expired" in notes
    if freshness["is_stale"]:
        return row.status in (MatchStatus.REVIEW_REQUIRED, MatchStatus.CONDITIONAL) and (
            "cited evidence is" in notes and "stale" in notes
        )
    return True


async def handle_capability_update(db: Session, entity_id: uuid.UUID, company_id: uuid.UUID, updates: dict) -> dict:
    result = capability_service.find_capability_by_id(db, entity_id, company_id)
    if result is None:
        raise NotFoundError(f"Capability entity '{entity_id}' not found.")
    entity_type, entity = result
    if entity.removed_at is not None:
        raise ConflictError(f"Capability entity '{entity_id}' has been removed and cannot be updated.")

    changed = capability_service.update_capability_fields(entity_type, entity, updates)
    if not changed:
        db.commit()
        return {"entity_id": entity_id, "changed_fields": [], "affected_missions": [], "new_recommendations": []}

    db.commit()
    db.refresh(entity)

    affected = find_affected_missions(db, entity_type, entity_id, company_id)
    reason = f"Capability {entity_id} ({entity_type.value}) updated: {', '.join(changed.keys())}"
    recommendations = await revalidate_missions(db, affected, company_id, reason) if affected else []

    return {
        "entity_id": entity_id,
        "changed_fields": list(changed.keys()),
        "affected_missions": [str(m) for m in affected],
        "new_recommendations": [str(r.id) for r in recommendations],
    }


async def handle_capability_removal(db: Session, entity_id: uuid.UUID, company_id: uuid.UUID) -> dict:
    result = capability_service.find_capability_by_id(db, entity_id, company_id)
    if result is None:
        raise NotFoundError(f"Capability entity '{entity_id}' not found.")
    entity_type, entity = result
    if entity.removed_at is not None:
        raise ConflictError(f"Capability entity '{entity_id}' has already been removed.")

    capability_service.soft_remove_capability(entity)
    db.commit()

    affected = find_affected_missions(db, entity_type, entity_id, company_id)
    reason = f"Capability {entity_id} ({entity_type.value}) removed"
    recommendations = await revalidate_missions(db, affected, company_id, reason) if affected else []

    return {
        "entity_id": entity_id,
        "affected_missions": [str(m) for m in affected],
        "new_recommendations": [str(r.id) for r in recommendations],
    }


async def run_freshness_sweep(db: Session, company_id: uuid.UUID) -> dict:
    """
    On-demand sweep (no scheduler exists anywhere in this project) using
    M4's evaluate_freshness, unchanged. Only entities that are currently
    expired/stale AND whose problem isn't already reflected in the
    affected mission's latest Recommendation trigger anything — this is
    what makes running the sweep twice in a row produce zero additional
    Recommendations the second time.
    """
    all_entities = capability_service.list_capabilities(db, company_id)
    missions_to_revalidate: dict[uuid.UUID, str] = {}

    for entity_type, entity in all_entities:
        freshness = evaluate_freshness(entity)
        if not freshness["is_expired"] and not freshness["is_stale"]:
            continue

        affected = find_affected_missions(db, entity_type, entity.id, company_id)
        for mission_id in affected:
            if mission_id in missions_to_revalidate:
                continue
            latest = decision_service.get_latest_recommendation_for_mission(db, mission_id)
            if latest is not None and _freshness_already_reflected(db, latest.id, entity_type, entity.id, freshness):
                continue
            state = "expired" if freshness["is_expired"] else "stale"
            missions_to_revalidate[mission_id] = f"Capability {entity.id} ({entity_type.value}) is now {state}"

    if not missions_to_revalidate:
        return {"missions_checked_affected": 0, "new_recommendations": []}

    all_new_recommendations = []
    for mission_id, reason in missions_to_revalidate.items():
        recs = await revalidate_missions(db, {mission_id}, company_id, reason)
        all_new_recommendations.extend(recs)

    return {
        "missions_checked_affected": len(missions_to_revalidate),
        "new_recommendations": [str(r.id) for r in all_new_recommendations],
    }

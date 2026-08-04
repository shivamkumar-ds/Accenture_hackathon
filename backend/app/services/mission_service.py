"""
Mission Orchestrator — workflow coordination only.

Calls tender_service.run_analysis() and decision_service.run_evaluation()
directly — the exact functions M5 and M6 already built and tested. No
extraction or matching logic is duplicated here; this module only
decides sequencing, state transitions, retries, and failure handling.

Stage-needed decisions use authoritative processing status
(Tender.processing_status, Mission.status), never the presence of
output rows — this is what keeps re-invocation resilient to future
event-driven re-analysis (M9): a status flip back to PENDING correctly
triggers re-execution regardless of what rows already exist.
"""

import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import AuditLog, Mission, Tender
from app.models.enums import DocumentProcessingStatus, MissionStatus
from app.services.exceptions import ConflictError, ExtractionError, NotFoundError

TENDER_ANALYSIS_AGENT = "tender_analysis_agent"
DECISION_ENGINE_AGENT = "decision_engine"
ORCHESTRATOR_AGENT = "mission_orchestrator"


def _log(db: Session, mission_id: uuid.UUID, user_id: uuid.UUID | None, agent: str, event: str, result: str = "") -> None:
    db.add(AuditLog(mission_id=mission_id, user_id=user_id, agent=agent, event=event, result=result))
    db.commit()


def get_mission(db: Session, mission_id: uuid.UUID, company_id: uuid.UUID) -> Mission:
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.company_id == company_id).one_or_none()
    if mission is None:
        raise NotFoundError(f"Mission '{mission_id}' not found.")
    return mission


def list_missions(db: Session, company_id: uuid.UUID) -> list[Mission]:
    return db.query(Mission).filter(Mission.company_id == company_id).order_by(Mission.created_at.desc()).all()


def archive_mission(db: Session, mission_id: uuid.UUID, company_id: uuid.UUID) -> Mission:
    """Soft-delete only — matches the Database Design's existing Active/Archived/Deleted
    principle, not a new pattern, and never a real DELETE."""
    mission = get_mission(db, mission_id, company_id)
    mission.status = MissionStatus.ARCHIVED
    db.commit()
    db.refresh(mission)
    return mission


def _try_transition_to_running(db: Session, mission: Mission, expected_status: MissionStatus) -> bool:
    """
    Bug #003 (docs/BUG_BUCKET.md): atomically flips a mission to RUNNING
    only if its status is still exactly what this request just read.

    execute_mission() used to do this as a plain read-then-write
    (`if mission.status == RUNNING: raise ...` followed by a separate
    `mission.status = RUNNING; db.commit()`), which is a classic
    check-then-act race: two concurrent execute requests for the same
    mission (a double-click, two open tabs, a retried request) can both
    read the pre-RUNNING status before either commits, both pass the
    check, and both proceed to run analysis/evaluation concurrently
    against the same mission — duplicate LLM calls, duplicate
    Requirement/Recommendation rows, and whichever commit lands last
    silently overwriting the other's state.

    This single `UPDATE ... WHERE id = :id AND status = :expected`
    is the atomic compare-and-swap: the database itself guarantees only
    one concurrent transaction's WHERE clause can still match by the
    time it runs, so only one caller ever gets a rowcount of 1. The
    loser gets rowcount 0 and must treat that as "already running/
    changed," matching the existing ConflictError contract.
    """
    result = db.execute(
        update(Mission)
        .where(Mission.id == mission.id, Mission.status == expected_status)
        .values(status=MissionStatus.RUNNING)
    )
    db.commit()
    return result.rowcount == 1


async def execute_mission(
    db: Session,
    mission_id: uuid.UUID,
    company_id: uuid.UUID,
    triggered_by: uuid.UUID,
    provider: str | None = None,
) -> Mission:
    # Imported locally, not at module level, to avoid a circular import:
    # decision_service now imports mission_service.get_mission (consolidating
    # duplicated lookup logic — see the M8 self-review), so this module
    # can't import decision_service at the top level without a cycle.
    from app.services import decision_service, tender_service

    mission = get_mission(db, mission_id, company_id)

    if mission.status in (MissionStatus.COMPLETED, MissionStatus.ARCHIVED):
        raise ConflictError(f"Mission '{mission_id}' is in a terminal state ({mission.status.value}) and cannot be executed.")
    if mission.status == MissionStatus.RUNNING:
        raise ConflictError(f"Mission '{mission_id}' is already running.")

    original_status = mission.status
    # Atomic compare-and-swap (Bug #003) — closes the race window between
    # the status checks above and this transition: if a concurrent
    # request already moved this mission out of `original_status`
    # (e.g. into RUNNING) between our read and this write, this returns
    # False instead of silently letting both requests proceed.
    if not _try_transition_to_running(db, mission, original_status):
        raise ConflictError(
            f"Mission '{mission_id}' was changed by another request just now — please retry."
        )
    db.refresh(mission)
    _log(db, mission.id, triggered_by, ORCHESTRATOR_AGENT, "Mission execution started")

    tender = db.query(Tender).filter(Tender.mission_id == mission.id).one_or_none()
    if tender is None:
        mission.status = original_status
        db.commit()
        raise NotFoundError(f"No tender found for mission '{mission_id}'.")

    analysis_ran = False
    if tender.processing_status != DocumentProcessingStatus.COMPLETED.value:
        _log(
            db, mission.id, triggered_by, TENDER_ANALYSIS_AGENT,
            f"Tender analysis required (current status: '{tender.processing_status}') — running",
        )
        try:
            await tender_service.run_analysis(db, tender.id, company_id, provider=provider)
            analysis_ran = True
            _log(db, mission.id, triggered_by, TENDER_ANALYSIS_AGENT, "Tender analysis completed")
        except ExtractionError as exc:
            mission.status = MissionStatus.CREATED  # revert — no FAILED value in the frozen enum; safe to retry
            db.commit()
            _log(db, mission.id, triggered_by, TENDER_ANALYSIS_AGENT, "Tender analysis failed", str(exc))
            raise
    else:
        _log(db, mission.id, triggered_by, TENDER_ANALYSIS_AGENT, "Tender analysis already completed — skipped")

    evaluation_already_done = original_status in (MissionStatus.AWAITING_APPROVAL, MissionStatus.COMPLETED)
    needs_evaluation = analysis_ran or not evaluation_already_done

    if needs_evaluation:
        _log(db, mission.id, triggered_by, DECISION_ENGINE_AGENT, "Running evaluation")
        try:
            await decision_service.run_evaluation(db, mission.id, company_id, provider=provider)
            _log(db, mission.id, triggered_by, DECISION_ENGINE_AGENT, "Evaluation completed")
        except ExtractionError as exc:
            mission.status = MissionStatus.CREATED
            db.commit()
            _log(db, mission.id, triggered_by, DECISION_ENGINE_AGENT, "Evaluation failed", str(exc))
            raise
    else:
        # decision_service.run_evaluation() sets Mission.status itself when it runs;
        # since it didn't run here, RUNNING (set above) needs to be restored manually.
        mission.status = original_status
        db.commit()
        _log(db, mission.id, triggered_by, DECISION_ENGINE_AGENT, "Evaluation already completed — skipped")

    _log(db, mission.id, triggered_by, ORCHESTRATOR_AGENT, "Mission execution finished")
    db.refresh(mission)
    return mission

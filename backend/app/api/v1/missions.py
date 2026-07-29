"""
Missions API.

GET/DELETE fill genuine gaps in 06_API_Design.md's Mission section
(never built until now). POST .../execute is a new endpoint — nothing
in the frozen doc names an execution trigger, same precedent as
/auth/register in M1.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import Document, Mission, Tender, User
from app.schemas.decision import RecommendationRead
from app.schemas.mission import ExecuteMissionRequest, MissionRead
from app.services import decision_service, mission_service
from app.services.exceptions import ConflictError, ExtractionError, NotFoundError

router = APIRouter(prefix="/missions", tags=["missions"])


def _attach_tender_info(db: Session, missions: list[Mission]) -> list[MissionRead]:
    """Enrich MissionRead with the real tender identity (see MissionRead's
    tender_id/tender_name comment). One batched query for both Tender and
    Document, regardless of how many missions are being listed, to avoid
    N+1 queries on the Dashboard/Tender Workspace list views."""
    if not missions:
        return []

    mission_ids = [m.id for m in missions]
    tenders = db.query(Tender).filter(Tender.mission_id.in_(mission_ids)).all()
    tender_by_mission = {t.mission_id: t for t in tenders}

    doc_ids = [t.uploaded_document for t in tenders if t.uploaded_document]
    doc_by_id = {}
    if doc_ids:
        doc_by_id = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}

    results = []
    for mission in missions:
        read = MissionRead.model_validate(mission)
        tender = tender_by_mission.get(mission.id)
        if tender is not None:
            read.tender_id = tender.id
            document = doc_by_id.get(tender.uploaded_document) if tender.uploaded_document else None
            # Prefer the name the user actually typed at upload; fall back
            # to the real uploaded file name -- never mission_type, which
            # is always the same fixed constant, not a tender identifier.
            read.tender_name = tender.tender_name or (document.file_name if document else None)
        results.append(read)
    return results


@router.get("", response_model=list[MissionRead])
def list_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MissionRead]:
    return _attach_tender_info(db, mission_service.list_missions(db, current_user.company_id))


@router.get("/{mission_id}", response_model=MissionRead)
def get_mission(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    try:
        mission = mission_service.get_mission(db, mission_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _attach_tender_info(db, [mission])[0]


@router.delete("/{mission_id}", response_model=MissionRead)
def archive_mission(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    """Archives (soft-delete), never a real DELETE — see mission_service.archive_mission."""
    try:
        return mission_service.archive_mission(db, mission_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# 10/minute per IP (Phase 1.5 finding #2) -- this is the Mission
# Orchestrator's own trigger for the full Decision Engine LLM run
# (mission_service.execute_mission -> decision_service.run_evaluation),
# the same cost profile /evaluation/run already carries a limit for.
# Left unrated until now was an oversight, not a deliberate exemption --
# every other cost-incurring endpoint already has this rate.
@router.post("/{mission_id}/execute", response_model=MissionRead)
@limiter.limit("10/minute")
async def execute_mission(
    request: Request,
    mission_id: uuid.UUID,
    payload: ExecuteMissionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    provider = payload.provider if payload else None
    try:
        return await mission_service.execute_mission(
            db, mission_id, current_user.company_id, current_user.id, provider=provider
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{mission_id}/recommendations", response_model=list[RecommendationRead])
def list_mission_recommendations(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecommendationRead]:
    """
    All Recommendations for this mission, oldest first — including any
    created by M9 revalidation after the mission was already completed.
    Mission.recommendation_id alone is not enough to see this: it
    deliberately keeps pointing at whatever was actually decided on.
    """
    try:
        mission_service.get_mission(db, mission_id, current_user.company_id)  # scoping check
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    recommendations = decision_service.get_recommendations_for_mission(db, mission_id)
    return [RecommendationRead.model_validate(r) for r in recommendations]

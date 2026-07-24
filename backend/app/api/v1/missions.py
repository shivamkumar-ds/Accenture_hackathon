"""
Missions API.

GET/DELETE fill genuine gaps in 06_API_Design.md's Mission section
(never built until now). POST .../execute is a new endpoint — nothing
in the frozen doc names an execution trigger, same precedent as
/auth/register in M1.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.decision import RecommendationRead
from app.schemas.mission import MissionRead
from app.services import decision_service, mission_service
from app.services.exceptions import ConflictError, ExtractionError, NotFoundError

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=list[MissionRead])
def list_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MissionRead]:
    return mission_service.list_missions(db, current_user.company_id)


@router.get("/{mission_id}", response_model=MissionRead)
def get_mission(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    try:
        return mission_service.get_mission(db, mission_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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


@router.post("/{mission_id}/execute", response_model=MissionRead)
async def execute_mission(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    try:
        return await mission_service.execute_mission(db, mission_id, current_user.company_id, current_user.id)
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

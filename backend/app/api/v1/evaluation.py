"""
Decision Intelligence API.

Two routers, matching 06_API_Design.md's two separate top-level paths
(/evaluation/... and /recommendations/...) — both describe nearly the
same response bundle under different names (a genuine doc ambiguity,
flagged during the implementation strategy and left unresolved rather
than guessed at). Both are implemented, backed by the same underlying
assembly function, since both are in the frozen, approved spec.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.decision import ComplianceMatrixEntryRead, EvaluationResponse, GapAnalysisEntry, RecommendationRead
from app.services import decision_service
from app.services.exceptions import ExtractionError, NotFoundError

evaluation_router = APIRouter(prefix="/evaluation", tags=["evaluation"])
recommendations_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RunEvaluationRequest(BaseModel):
    mission_id: uuid.UUID


def _build_response(db: Session, recommendation, compliance_rows, requirements_by_id) -> EvaluationResponse:
    # Evidence trail resolution (DESIGN_SYSTEM.md §10: Recommendation ->
    # Evidence -> Source Clause -> Company Document) — source_page comes
    # from the already-fetched Requirement, evidence_source is resolved
    # via decision_service.resolve_evidence_sources(). Both are attached
    # with model_copy(update=...) rather than passed into model_validate(),
    # since neither lives on the ComplianceMatrix ORM row itself.
    evidence_sources = decision_service.resolve_evidence_sources(db, compliance_rows)
    compliance_matrix = [
        ComplianceMatrixEntryRead.model_validate(row).model_copy(
            update={
                "source_page": requirements_by_id[row.requirement_id].source_page,
                "evidence_source": evidence_sources.get(row.evidence_reference),
            }
        )
        for row in compliance_rows
    ]
    gap_analysis = [
        GapAnalysisEntry(
            requirement_id=row.requirement_id,
            requirement_type=requirements_by_id[row.requirement_id].requirement_type,
            description=requirements_by_id[row.requirement_id].description,
            mandatory=requirements_by_id[row.requirement_id].mandatory,
            status=row.status,
            reason=row.verification_reason or row.notes,
            source_page=requirements_by_id[row.requirement_id].source_page,
        )
        for row in compliance_rows
        if row.status.value != "met"
    ]
    return EvaluationResponse(
        recommendation=RecommendationRead.model_validate(recommendation),
        compliance_matrix=compliance_matrix,
        gap_analysis=gap_analysis,
    )


@evaluation_router.post("/run", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    payload: RunEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationResponse:
    try:
        await decision_service.run_evaluation(db, payload.mission_id, current_user.company_id)
        recommendation, compliance_rows, requirements_by_id = decision_service.get_evaluation_bundle(
            db, payload.mission_id, current_user.company_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _build_response(db, recommendation, compliance_rows, requirements_by_id)


@evaluation_router.get("/{mission_id}", response_model=EvaluationResponse)
def get_evaluation(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationResponse:
    try:
        recommendation, compliance_rows, requirements_by_id = decision_service.get_evaluation_bundle(
            db, mission_id, current_user.company_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_response(db, recommendation, compliance_rows, requirements_by_id)


@recommendations_router.get("/{mission_id}", response_model=EvaluationResponse)
def get_recommendation(
    mission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationResponse:
    # Same assembly as GET /evaluation/{mission_id} — see module docstring.
    try:
        recommendation, compliance_rows, requirements_by_id = decision_service.get_evaluation_bundle(
            db, mission_id, current_user.company_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_response(db, recommendation, compliance_rows, requirements_by_id)

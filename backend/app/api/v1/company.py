"""Company API — Create and Read endpoints (the M0 vertical slice)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.company import CompanyCreate, CompanyRead
from app.services import company_service
from app.services.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/company", tags=["company"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> CompanyRead:
    try:
        return company_service.create_company(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyRead:
    """
    M10 audit finding: this endpoint had no authentication at all — a
    real gap dating back to M0 (built before M1 introduced auth), never
    revisited since. Fixed to match the pattern every other endpoint in
    the system already follows: authenticated, and scoped so a user can
    only view their own company — a 404, not 403, for anything else,
    consistent with never revealing whether something exists for a
    tenant that isn't yours (same principle used everywhere since M1).
    """
    if company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Company '{company_id}' not found.")
    try:
        return company_service.get_company(db, company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

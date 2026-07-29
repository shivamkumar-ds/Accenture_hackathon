"""
Company API — Read endpoint only.

RC-1 audit finding A1: this file used to also expose `POST /company`, a
leftover from the M0 vertical slice built before M1 introduced auth. It
created a bare Company row with no authentication dependency at all and no
associated user, duplicating (and bypassing) auth_service.register() —
the correct, atomic Company+Administrator creation path every real signup
actually uses. An unauthenticated endpoint that writes to the database is
a spam/resource-exhaustion vector, and every company it created was
permanently orphaned (no user could ever log into it). Removed rather
than fixed-in-place, since /auth/register already covers this need
correctly — confirmed via grep that the frontend never called this route.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.company import CompanyRead
from app.services import company_service

router = APIRouter(prefix="/company", tags=["company"])


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
    return company_service.get_company(db, company_id)

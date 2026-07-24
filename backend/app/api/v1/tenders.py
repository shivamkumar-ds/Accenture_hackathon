"""
Tender and Analysis APIs.

Two routers in one file (not one file each) since both concern the same
subject — tender analysis — and 06_API_Design.md itself specifies them
as separate top-level paths (/tenders/... and /analysis/...), not
nested under a shared prefix.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.tender import (
    RequirementRead,
    TenderRead,
    TenderUploadResult,
    TenderWithRequirements,
)
from app.services import tender_service
from app.services.exceptions import ExtractionError, NotFoundError

tenders_router = APIRouter(prefix="/tenders", tags=["tenders"])
analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])


@tenders_router.post(
    "/upload", response_model=TenderUploadResult, status_code=status.HTTP_201_CREATED
)
async def upload_tender(
    file: UploadFile = File(...),
    tender_name: str | None = Form(None),
    organization: str | None = Form(None),
    closing_date: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderUploadResult:
    mission, tender = await tender_service.upload_tender(
        db, current_user.company_id, current_user.id, file, tender_name, organization, closing_date
    )
    return TenderUploadResult(tender_id=tender.id, mission_id=mission.id)


@tenders_router.get("/{tender_id}", response_model=TenderWithRequirements)
def get_tender(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderWithRequirements:
    try:
        tender = tender_service.get_tender(db, tender_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    requirements = tender_service.get_requirements(db, tender.id)
    return TenderWithRequirements(
        tender=TenderRead.model_validate(tender),
        requirements=[RequirementRead.model_validate(r) for r in requirements],
    )


class RunAnalysisRequest(BaseModel):
    tender_id: uuid.UUID


@analysis_router.post("/run", response_model=TenderWithRequirements)
async def run_analysis(
    payload: RunAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderWithRequirements:
    try:
        tender, requirements = await tender_service.run_analysis(
            db, payload.tender_id, current_user.company_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return TenderWithRequirements(
        tender=TenderRead.model_validate(tender),
        requirements=[RequirementRead.model_validate(r) for r in requirements],
    )

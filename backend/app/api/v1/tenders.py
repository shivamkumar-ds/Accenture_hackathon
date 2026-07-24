"""
Tender and Analysis APIs.

Two routers in one file (not one file each) since both concern the same
subject — tender analysis — and 06_API_Design.md itself specifies them
as separate top-level paths (/tenders/... and /analysis/...), not
nested under a shared prefix.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import User
from app.schemas.tender import (
    RequirementRead,
    TenderRead,
    TenderUploadResult,
    TenderWithRequirements,
)
from app.services import tender_service
from app.services.exceptions import ExtractionError, FileTooLargeError, NotFoundError, UnsupportedFileTypeError

tenders_router = APIRouter(prefix="/tenders", tags=["tenders"])
analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])


# 20/minute per IP (RC-2 finding H-2) — same reasoning as /documents/upload.
@tenders_router.post(
    "/upload", response_model=TenderUploadResult, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
async def upload_tender(
    request: Request,
    file: UploadFile = File(...),
    tender_name: str | None = Form(None),
    organization: str | None = Form(None),
    closing_date: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderUploadResult:
    # RC-1 audit finding B1: tender_service.upload_tender() calls the same
    # document_service.upload_document() that POST /documents/upload uses,
    # capable of raising the same two exceptions -- this router previously
    # had no try/except at all, so an oversized or wrong-type tender file
    # produced an unhandled 500 instead of the clean 413/415 that
    # /documents/upload already returns for the identical underlying error.
    try:
        mission, tender = await tender_service.upload_tender(
            db, current_user.company_id, current_user.id, file, tender_name, organization, closing_date
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
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


# 10/minute per IP (RC-2 finding H-2) — this triggers a real LLM call per
# tender-page chunk; the single most expensive endpoint per invocation
# after decision evaluation itself.
@analysis_router.post("/run", response_model=TenderWithRequirements)
@limiter.limit("10/minute")
async def run_analysis(
    request: Request,
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

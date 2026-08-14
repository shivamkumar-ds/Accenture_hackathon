"""
Tender and Analysis APIs.

Two routers in one file (not one file each) since both concern the same
subject — tender analysis — and 06_API_Design.md itself specifies them
as separate top-level paths (/tenders/... and /analysis/...), not
nested under a shared prefix.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import User
from app.schemas.tender import (
    RequirementRead,
    TenderDocumentRead,
    TenderMetadataGuess,
    TenderRead,
    TenderUploadResult,
    TenderWithRequirements,
)
from app.services import tender_service

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
    category: str | None = Form(None),
    closing_date: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderUploadResult:
    # RC-1 audit finding B1: tender_service.upload_tender() calls the same
    # document_service.upload_document() that POST /documents/upload uses,
    # capable of raising the same two exceptions (UnsupportedFileTypeError,
    # FileTooLargeError) -- both now map to the same clean 415/413 via the
    # centralized handler in app/core/exception_handlers.py (Phase 1.5 #4+5).
    mission, tender = await tender_service.upload_tender(
        db, current_user.company_id, current_user.id, file, tender_name, organization, closing_date, category
    )
    return TenderUploadResult(tender_id=tender.id, mission_id=mission.id)


# 20/minute per IP -- same budget as /tenders/upload since it does the same
# PDF-read work, just without persisting anything.
@tenders_router.post("/extract-metadata", response_model=TenderMetadataGuess)
@limiter.limit("20/minute")
async def extract_metadata(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> TenderMetadataGuess:
    guess = await tender_service.extract_tender_metadata(file)
    return TenderMetadataGuess(**guess)


@tenders_router.get("/{tender_id}", response_model=TenderWithRequirements)
def get_tender(
    tender_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderWithRequirements:
    tender = tender_service.get_tender(db, tender_id, current_user.company_id)
    requirements = tender_service.get_requirements(db, tender.id)
    documents = tender_service.list_tender_documents(db, tender.id, current_user.company_id)
    return TenderWithRequirements(
        tender=TenderRead.model_validate(tender),
        requirements=[RequirementRead.model_validate(r) for r in requirements],
        documents=[TenderDocumentRead.model_validate(d) for d in documents],
    )


# 20/minute per IP -- same budget as /tenders/upload, which this reuses
# document_service.upload_document()'s validation/storage path for (so
# PDF/XLS/XLSX are accepted, everything else rejected, identically).
@tenders_router.post(
    "/{tender_id}/documents", response_model=TenderDocumentRead, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
async def add_tender_document(
    request: Request,
    tender_id: uuid.UUID,
    file: UploadFile = File(...),
    document_role: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenderDocumentRead:
    document = await tender_service.add_tender_document(
        db, tender_id, current_user.company_id, current_user.id, file, document_role
    )
    return TenderDocumentRead.model_validate(document)


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
    tender, requirements = await tender_service.run_analysis(
        db, payload.tender_id, current_user.company_id
    )
    documents = tender_service.list_tender_documents(db, tender.id, current_user.company_id)

    return TenderWithRequirements(
        tender=TenderRead.model_validate(tender),
        requirements=[RequirementRead.model_validate(r) for r in requirements],
        documents=[TenderDocumentRead.model_validate(d) for d in documents],
    )

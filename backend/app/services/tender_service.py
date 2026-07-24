"""
Tender service.

upload_tender() implements 06_API_Design.md's existing contract (tender
upload returns both Tender ID and Mission ID) — it creates a minimal,
inert Mission row alongside the Tender, with no orchestration logic.
State transitions and agent coordination remain M7's job; this Mission
just exists in CREATED status until M7 can drive it.

Company scoping goes through Tender -> Mission -> company_id, since
Tender has no company_id column of its own.
"""

import uuid
from datetime import date

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.agents import tender_analyzer
from app.core import storage
from app.models import Document, Mission, Requirement, Tender
from app.models.enums import DocumentProcessingStatus, MissionStatus, RequirementType
from app.services import document_service
from app.services.exceptions import ExtractionError, NotFoundError


async def upload_tender(
    db: Session,
    company_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    file: UploadFile,
    tender_name: str | None = None,
    organization: str | None = None,
    closing_date: date | None = None,
) -> tuple[Mission, Tender]:
    document = await document_service.upload_document(db, company_id, uploaded_by, "tender", file)

    mission = Mission(
        company_id=company_id,
        user_id=uploaded_by,
        mission_type="tender_evaluation",
        status=MissionStatus.CREATED,
    )
    db.add(mission)
    db.flush()  # assigns mission.id without committing yet

    tender = Tender(
        mission_id=mission.id,
        tender_name=tender_name,
        organization=organization,
        closing_date=closing_date,
        uploaded_document=document.id,
        processing_status=DocumentProcessingStatus.PENDING.value,
    )
    db.add(tender)
    db.commit()
    db.refresh(mission)
    db.refresh(tender)
    return mission, tender


def get_tender(db: Session, tender_id: uuid.UUID, company_id: uuid.UUID) -> Tender:
    tender = (
        db.query(Tender)
        .join(Mission, Tender.mission_id == Mission.id)
        .filter(Tender.id == tender_id, Mission.company_id == company_id)
        .one_or_none()
    )
    if tender is None:
        raise NotFoundError(f"Tender '{tender_id}' not found.")
    return tender


def get_requirements(db: Session, tender_id: uuid.UUID) -> list[Requirement]:
    return (
        db.query(Requirement)
        .filter(Requirement.tender_id == tender_id)
        .order_by(Requirement.source_page)
        .all()
    )


async def run_analysis(
    db: Session, tender_id: uuid.UUID, company_id: uuid.UUID, provider: str | None = None
) -> tuple[Tender, list[Requirement]]:
    tender = get_tender(db, tender_id, company_id)  # raises NotFoundError if not this company's

    tender.processing_status = DocumentProcessingStatus.PROCESSING.value
    db.commit()

    document = db.get(Document, tender.uploaded_document)
    file_path = storage.resolve_path(document.storage_path)

    try:
        results = await tender_analyzer.analyze_tender(file_path, provider=provider)
    except Exception as exc:
        tender.processing_status = DocumentProcessingStatus.FAILED.value
        db.commit()
        raise ExtractionError(f"Tender analysis failed for tender '{tender_id}': {exc}") from exc

    requirement_rows = []
    for result in results:
        requirement = Requirement(
            tender_id=tender.id,
            requirement_type=RequirementType(result.requirement_type),
            description=result.description,
            mandatory=result.mandatory,
            source_page=result.source_page,
            confidence=result.confidence,
        )
        db.add(requirement)
        requirement_rows.append(requirement)

    tender.processing_status = DocumentProcessingStatus.COMPLETED.value
    db.commit()
    for requirement in requirement_rows:
        db.refresh(requirement)

    return tender, requirement_rows

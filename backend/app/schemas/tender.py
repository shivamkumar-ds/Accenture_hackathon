"""Pydantic schemas for Tender and Requirement."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import RequirementType


class TenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    tender_name: str | None
    organization: str | None
    closing_date: date | None
    uploaded_document: uuid.UUID | None
    processing_status: str | None


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    requirement_type: RequirementType
    description: str | None
    mandatory: bool
    source_page: int | None
    confidence: float | None


class TenderWithRequirements(BaseModel):
    tender: TenderRead
    requirements: list[RequirementRead]


class TenderUploadResult(BaseModel):
    """Response schema for POST /tenders/upload.

    Added during the BidOps_Final consolidation (99_DECISIONS_LOG.md D-144) to
    close the last gap between what this endpoint actually returns and what
    the OpenAPI spec/frontend can rely on at compile time -- this exact field
    (tender_id) was previously the subject of a real frontend/backend contract
    bug (D-143 background), fixed there by correcting the frontend's assumed
    field name. This schema fixes the other side: the endpoint now declares
    its response shape instead of returning a bare, untyped dict.
    """

    tender_id: uuid.UUID
    mission_id: uuid.UUID

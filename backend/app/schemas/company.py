"""Pydantic schemas for Company — the request/response contract for the API layer."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyCreate(BaseModel):
    name: str
    industry: str | None = None
    registration_number: str
    country: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    registration_number: str
    country: str | None
    created_at: datetime
    updated_at: datetime

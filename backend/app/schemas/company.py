"""
Pydantic schemas for Company — the request/response contract for the API layer.

CompanyCreate was removed as part of RC-1 audit finding A1 (POST /company
removed — see app/api/v1/company.py's module docstring). Company creation
now only happens atomically with its first Administrator, via
RegisterRequest (app/schemas/auth.py) and auth_service.register().
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    registration_number: str
    country: str | None
    created_at: datetime
    updated_at: datetime

"""
Company service — business logic layer for Company entities.

Even though this first slice is plain CRUD, it stays in the service
layer rather than inline in the router, so the router/service/model
separation exists from the first endpoint rather than being retrofitted
once real business logic (Capability Builder, Decision Intelligence)
arrives.

create_company() was removed as part of RC-1 audit finding A1 — it
duplicated auth_service.register()'s Company+Administrator creation but
had no way to attach a user, and was exposed through an unauthenticated
router endpoint. Company creation is now exclusively the atomic path in
auth_service.register().
"""

import uuid

from sqlalchemy.orm import Session

from app.models import Company
from app.services.exceptions import NotFoundError


def get_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company '{company_id}' not found.")
    return company

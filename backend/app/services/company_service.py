"""
Company service — business logic layer for Company entities.

Even though this first slice is plain CRUD, it stays in the service
layer rather than inline in the router, so the router/service/model
separation exists from the first endpoint rather than being retrofitted
once real business logic (Capability Builder, Decision Intelligence)
arrives.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Company
from app.schemas.company import CompanyCreate
from app.services.exceptions import ConflictError, NotFoundError


def create_company(db: Session, data: CompanyCreate) -> Company:
    company = Company(
        name=data.name,
        industry=data.industry,
        registration_number=data.registration_number,
        country=data.country,
    )
    db.add(company)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"A company with registration number '{data.registration_number}' already exists."
        ) from exc
    db.refresh(company)
    return company


def get_company(db: Session, company_id: uuid.UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company '{company_id}' not found.")
    return company

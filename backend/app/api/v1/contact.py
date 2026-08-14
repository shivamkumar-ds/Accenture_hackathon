"""
Contact API — the public "Contact Us" form. Deliberately the one
endpoint in this API meant to be reachable by a visitor who has never
created a BidOps account: no `Depends(get_current_user)`, no company
scoping, nothing else assumed about the caller.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.contact import ContactRequest, ContactResponse
from app.services import contact_service

router = APIRouter(prefix="/contact", tags=["contact"])


# 5/hour per IP -- deliberately chosen for *this* endpoint's own usage
# pattern, not copied from /auth/register's 5/hour (which exists for a
# different reason entirely: gating free account creation). A genuine
# visitor submits this form once, maybe twice after fixing a validation
# error; five is generous headroom for that while still bounding the
# email volume and DB writes a single abusive IP can generate against an
# endpoint that requires no account and, per the governing spec, no
# CAPTCHA.
@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def submit_contact(
    request: Request, payload: ContactRequest, db: Session = Depends(get_db)
) -> ContactResponse:
    submission = contact_service.submit_contact_form(db, payload)
    if submission is None:
        # Honeypot hit (see ContactRequest.website) -- respond with an
        # identical-shaped 201 without ever having touched the database,
        # so a bot gets no signal that its submission was treated any
        # differently from a real one.
        return ContactResponse(id=uuid.uuid4(), created_at=datetime.now(timezone.utc))
    return ContactResponse(id=submission.id, created_at=submission.created_at)

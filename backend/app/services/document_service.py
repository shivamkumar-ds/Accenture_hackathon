"""
Document service — business logic for Document entities.

get_document() is company-scoped by design: it takes the requesting
user's company_id and treats a document belonging to a different
company exactly like a document that doesn't exist (NotFoundError,
mapped to a 404 by the router) — never a distinguishable error that
would let one tenant infer another tenant's document IDs exist.
"""

import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import storage
from app.models import Document
from app.services.exceptions import NotFoundError


async def upload_document(
    db: Session,
    company_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    document_type: str,
    file: UploadFile,
) -> Document:
    storage.validate_file_type(file.filename, file.content_type)
    relative_path, _unique_filename, _size = await storage.save_upload(company_id, file)

    document = Document(
        company_id=company_id,
        uploaded_by=uploaded_by,
        document_type=document_type,
        file_name=file.filename or "unnamed",
        storage_path=relative_path,
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.resolve_path(relative_path).unlink(missing_ok=True)
        raise
    db.refresh(document)
    return document


def get_document(db: Session, document_id: uuid.UUID, company_id: uuid.UUID) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.company_id == company_id)
        .one_or_none()
    )
    if document is None:
        raise NotFoundError(f"Document '{document_id}' not found.")
    return document


def list_documents(db: Session, company_id: uuid.UUID) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.company_id == company_id)
        .order_by(Document.upload_time.desc())
        .all()
    )

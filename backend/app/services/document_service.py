"""
Document service — business logic for Document entities.

get_document() is company-scoped by design: it takes the requesting
user's company_id and treats a document belonging to a different
company exactly like a document that doesn't exist (NotFoundError,
mapped to a 404 by the router) — never a distinguishable error that
would let one tenant infer another tenant's document IDs exist.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import storage
from app.models import Document, Mission, Tender
from app.models.enums import MissionStatus
from app.services.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


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
        logger.exception(
            "Document upload failed, rolling back: company_id=%s document_type=%s file_name=%s",
            company_id,
            document_type,
            file.filename,
        )
        db.rollback()
        # storage.delete_file() (not resolve_path().unlink()) -- backend-
        # agnostic (Phase 3: GCP deployment). The old local-only cleanup
        # left an orphaned GCS blob behind on this exact failure path once
        # STORAGE_BACKEND=gcs, since resolve_path() only ever produces a
        # local filesystem path that was never actually written to.
        storage.delete_file(relative_path)
        raise
    db.refresh(document)
    return document


def get_document(db: Session, document_id: uuid.UUID, company_id: uuid.UUID) -> Document:
    # Deliberately NOT filtered by removed_at -- a deleted document's row
    # still needs to resolve by ID for internal lookups (e.g. tender_service
    # resolving Tender.uploaded_document), same reasoning as
    # capability_service.find_capability_by_id vs list_capabilities.
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.company_id == company_id)
        .one_or_none()
    )
    if document is None:
        raise NotFoundError(f"Document '{document_id}' not found.")
    return document


def list_documents(db: Session, company_id: uuid.UUID) -> list[Document]:
    # Excludes soft-deleted documents -- same Active/Archived/Deleted
    # convention as list_capabilities() excluding removed_at rows.
    return (
        db.query(Document)
        .filter(Document.company_id == company_id, Document.removed_at.is_(None))
        .order_by(Document.upload_time.desc())
        .all()
    )


def delete_document(db: Session, document_id: uuid.UUID, company_id: uuid.UUID) -> Document:
    """
    Soft-deletes the Document row (removed_at) and unlinks the real file
    from disk -- the row survives so any existing FK reference (a Tender,
    a capability entity's source_document_id, an audit trail) still
    resolves, but the content itself is genuinely gone and the document
    stops appearing anywhere in the UI.

    Blocked (ConflictError, not a silent cascade) if:
    - A non-archived Tender still references this document -- deleting
      the document out from under a live tender/mission would break
      "View Details"/re-run analysis for that mission. The user has to
      archive the tender first (an explicit, visible action) rather
      than have it silently orphaned.
    - Any capability entity still has this document as its
      source_document_id and hasn't been removed -- same reasoning:
      deleting a document that capability evidence still points to
      would leave that capability's provenance dangling. The user
      deletes the capability entry first (already wired up via
      DELETE /capabilities/{entity_id}), which is the explicit,
      cascade-revalidation-aware path that already exists for that.
    """
    document = get_document(db, document_id, company_id)
    if document.removed_at is not None:
        raise ConflictError(f"Document '{document_id}' has already been deleted.")

    # Generalized for multi-document tenders: document.tender_id covers
    # BOTH the original "main" document and any additional document
    # attached via POST /tenders/{id}/documents; the OR against the
    # legacy Tender.uploaded_document column is a backward-compat
    # safety net for any pre-migration row the backfill might have
    # missed, not the primary check anymore.
    blocking_tender = (
        db.query(Tender)
        .join(Mission, Tender.mission_id == Mission.id)
        .filter(
            (Tender.uploaded_document == document_id) | (Tender.id == document.tender_id),
            Mission.status != MissionStatus.ARCHIVED,
        )
        .first()
    )
    if blocking_tender is not None:
        raise ConflictError(
            f"Document '{document_id}' is still attached to an active tender. "
            "Delete that tender first."
        )

    # Local import -- capability_service already imports document_service
    # (get_document), so importing it back at module level here would be
    # circular; deferred the same way mission_service defers its own
    # cross-service imports inside execute_mission().
    from app.services import capability_service

    if capability_service.document_has_active_capabilities(db, document_id):
        raise ConflictError(
            f"Document '{document_id}' still has capabilities built from it. "
            "Delete the capability entry first."
        )

    storage.delete_file(document.storage_path)
    document.removed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return document

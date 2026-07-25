"""
Documents API. Every operation requires authentication; every read and
write is scoped to the current user's own company — never another
tenant's, regardless of role.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import storage
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import User
from app.schemas.document import DocumentRead
from app.services import document_service
from app.services.exceptions import ConflictError, FileTooLargeError, NotFoundError, UnsupportedFileTypeError

router = APIRouter(prefix="/documents", tags=["documents"])


# 20/minute per IP (RC-2 finding H-2) — every upload costs real disk space
# and, for capability documents, a downstream LLM extraction call.
@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        return await document_service.upload_document(
            db, current_user.company_id, current_user.id, document_type, file
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc


@router.get("", response_model=list[DocumentRead])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    return document_service.list_documents(db, current_user.company_id)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        return document_service.get_document(db, document_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{document_id}", response_model=DocumentRead)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    """Soft-delete + real file removal -- see document_service.delete_document
    for the exact blocking conditions (active tender / active capability
    still referencing it)."""
    try:
        return document_service.delete_document(db, document_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        document = document_service.get_document(db, document_id, current_user.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    file_path = storage.resolve_path(document.storage_path)
    if not file_path.exists():
        # The DB row exists but the file is missing on disk — a real,
        # distinct failure mode from "document not found", worth its own message.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document metadata exists but the underlying file is missing.",
        )
    return FileResponse(path=file_path, filename=document.file_name)

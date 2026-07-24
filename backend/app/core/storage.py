"""
Local disk document storage (M2 — MVP acceptable per the Execution Plan).

Functions, not a class hierarchy: there's exactly one implementation
today, so an abstract storage interface for a hypothetical future S3
backend would be complexity with no present payoff. Callers pass a
company_id and an UploadFile and get back a relative storage path —
that signature doesn't need to change when a real object-storage
backend eventually replaces this module.

Layout: storage/{company_id}/documents/{uuid}.{ext} — keeps filesystem
organization aligned with tenant isolation now, and maps directly onto
an S3 key prefix later (company_id becomes the prefix).
"""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.services.exceptions import FileTooLargeError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)
settings = get_settings()

STORAGE_ROOT = Path(settings.storage_root)
CHUNK_SIZE = 1024 * 1024  # 1MB — read/write in chunks so size is enforced during streaming, not after

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}


def validate_file_type(filename: str, content_type: str | None) -> None:
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(
            "Upload rejected — unsupported file type: filename=%r content_type=%r", filename, content_type
        )
        raise UnsupportedFileTypeError(
            f"Unsupported file type: '{filename}' ({content_type}). "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )


async def save_upload(company_id: uuid.UUID, upload: UploadFile) -> tuple[str, str, int]:
    """
    Streams the upload to disk under storage/{company_id}/documents/,
    enforcing the size limit while writing rather than after a full
    in-memory read (which would defeat the point of a size limit).

    Returns (relative_storage_path, unique_filename, size_in_bytes).
    Raises FileTooLargeError if the configured max is exceeded — any
    partial file written so far is removed.
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    extension = Path(upload.filename or "").suffix.lower()
    unique_filename = f"{uuid.uuid4()}{extension}"

    company_dir = STORAGE_ROOT / str(company_id) / "documents"
    company_dir.mkdir(parents=True, exist_ok=True)
    dest_path = company_dir / unique_filename

    size = 0
    try:
        with open(dest_path, "wb") as out_file:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLargeError(
                        f"File exceeds the maximum allowed size of {settings.max_upload_size_mb}MB."
                    )
                out_file.write(chunk)
    except FileTooLargeError:
        logger.warning(
            "Upload rejected — exceeded %sMB size limit: company_id=%s", settings.max_upload_size_mb, company_id
        )
        dest_path.unlink(missing_ok=True)
        raise

    relative_path = str(dest_path.relative_to(STORAGE_ROOT))
    return relative_path, unique_filename, size


def resolve_path(relative_storage_path: str) -> Path:
    """Resolves a stored relative path back to an absolute filesystem path for retrieval."""
    return STORAGE_ROOT / relative_storage_path

"""
Document storage — local disk (M2, still the default) or Google Cloud
Storage (Phase 3: GCP deployment), selected by `settings.storage_backend`.

Every function below keeps its exact original signature and the exact
same {company_id}/documents/{uuid}.{ext} relative-path key layout
regardless of backend -- Document.storage_path in the database never
changes shape, so switching STORAGE_BACKEND requires no data migration
for documents uploaded before the switch, only that they physically exist
wherever the new backend expects them (see docs/DEPLOYMENT.md's File
Storage section for the one-time copy step when cutting over an existing
deployment).

Why this exists at all: Cloud Run's container filesystem is ephemeral and
never shared across instances. A file saved to local disk by one request
may not exist when a later request (possibly a different instance
entirely) tries to read it back -- silent data loss in production, not a
theoretical concern. STORAGE_BACKEND=gcs is the production-safe choice on
Cloud Run; STORAGE_BACKEND=local (default, unchanged) remains correct for
local development, where there's exactly one process and the filesystem
genuinely persists across a request.

Functions, not a class hierarchy, same reasoning as before this phase:
there are now two implementations, but callers never choose between them
-- one env var does, and every call site stays backend-agnostic.
"""

import logging
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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


def _gcs_bucket():
    """Local import — google-cloud-storage is only required when
    STORAGE_BACKEND=gcs; a local-backend deployment (or the test suite,
    which never touches this) doesn't need the dependency importable."""
    from google.cloud import storage as gcs

    return gcs.Client().bucket(settings.gcs_bucket_name)


async def save_upload(company_id: uuid.UUID, upload: UploadFile) -> tuple[str, str, int]:
    """
    Streams the upload to storage under {company_id}/documents/, enforcing
    the size limit while writing rather than after a full in-memory read
    (which would defeat the point of a size limit) -- true for both
    backends.

    Returns (relative_storage_path, unique_filename, size_in_bytes).
    Raises FileTooLargeError if the configured max is exceeded — any
    partial file/blob written so far is removed.
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    extension = Path(upload.filename or "").suffix.lower()
    unique_filename = f"{uuid.uuid4()}{extension}"
    relative_path = f"{company_id}/documents/{unique_filename}"

    size = 0
    if settings.storage_backend == "gcs":
        blob = _gcs_bucket().blob(relative_path)
        try:
            with blob.open("wb") as out_file:
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
            try:
                blob.delete()
            except Exception:
                pass  # partial/no blob to clean up -- not itself an error, see delete_file()'s reasoning
            raise
        return relative_path, unique_filename, size

    company_dir = STORAGE_ROOT / str(company_id) / "documents"
    company_dir.mkdir(parents=True, exist_ok=True)
    dest_path = company_dir / unique_filename

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
    """
    Local-backend only: resolves a stored relative path back to an
    absolute filesystem path. Callers that need to actually read a
    document's bytes (tender analysis, capability extraction) must use
    `local_file_for_read()` below instead -- this stays as a thin,
    backend-specific helper because a handful of call sites (e.g. building
    a display path) never need to work against GCS at all.
    """
    return STORAGE_ROOT / relative_storage_path


@contextmanager
def local_file_for_read(relative_storage_path: str) -> Iterator[Path]:
    """
    Backend-agnostic: yields a real, local filesystem Path to a document's
    contents, regardless of where it's actually stored. Every parser in
    this codebase (pypdf, pdf2image/pytesseract, python-docx) needs a real
    local path or file handle, not a remote URL -- this is the one seam
    that isolates them from ever needing to know about GCS.

    Local backend: yields the existing on-disk path directly, no copy.
    GCS backend: downloads the blob into a temporary file (cleaned up on
    exit, success or failure) and yields that path instead.
    """
    if settings.storage_backend == "gcs":
        extension = Path(relative_storage_path).suffix
        blob = _gcs_bucket().blob(relative_storage_path)
        with tempfile.NamedTemporaryFile(suffix=extension, delete=True) as tmp:
            blob.download_to_filename(tmp.name)
            yield Path(tmp.name)
        return

    yield resolve_path(relative_storage_path)


def generate_download_url(relative_storage_path: str, expires_seconds: int = 900) -> str | None:
    """
    GCS backend only: a short-lived signed URL so the browser downloads
    directly from Cloud Storage instead of the request being proxied
    through the Cloud Run backend (bandwidth, latency, and Cloud Run
    request-time billing all favor this). Returns None for the local
    backend -- the caller (GET /documents/{id}/download) falls back to
    serving the file directly via FileResponse in that case, exactly as
    it always has.
    """
    if settings.storage_backend != "gcs":
        return None
    blob = _gcs_bucket().blob(relative_storage_path)
    from datetime import timedelta

    return blob.generate_signed_url(expiration=timedelta(seconds=expires_seconds), method="GET")


def delete_file(relative_storage_path: str) -> None:
    """Removes the stored file/blob for a deleted Document. Not an error if
    it's already gone (e.g. a second delete attempt racing, or manual
    cleanup) -- the DB row's removed_at is the source of truth for
    "deleted", not the file's existence, for both backends."""
    if settings.storage_backend == "gcs":
        blob = _gcs_bucket().blob(relative_storage_path)
        try:
            blob.delete()
        except Exception as exc:
            # google-cloud-storage raises google.api_core.exceptions.NotFound
            # for a missing blob -- caught broadly here (rather than
            # importing that exception type just for this) since any
            # "already gone" outcome is equally a no-op; a genuine
            # connectivity/permission problem still surfaces immediately on
            # the *next* real GCS call this request makes, it's just not
            # this best-effort cleanup's job to report it.
            logger.info("GCS delete for '%s' did not remove an existing blob: %s", relative_storage_path, exc)
        return

    resolve_path(relative_storage_path).unlink(missing_ok=True)

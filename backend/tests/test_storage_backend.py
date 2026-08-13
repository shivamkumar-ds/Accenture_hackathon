"""
Regression coverage for the storage backend abstraction added in Phase 3
(GCP deployment): app/core/storage.py now supports STORAGE_BACKEND=local
(default, unchanged M2 behavior) or STORAGE_BACKEND=gcs.

The GCS cases here never import or contact real Google Cloud Storage --
they monkeypatch storage._gcs_bucket(), the one seam every GCS-backed
function goes through, with an in-memory fake. What's under test is
BidOps' own logic: that local_file_for_read() actually downloads to a
real local path and cleans it up afterward, that generate_download_url()
only returns something for the gcs backend, and that delete_file() is
backend-agnostic (the exact gap that would have leaked an orphaned GCS
blob on a failed document-upload commit -- see the fix in
document_service.py's upload_document()).
"""

from pathlib import Path

import pytest

from app.core import storage


class _FakeBlob:
    def __init__(self, store: dict, key: str):
        self._store = store
        self._key = key

    def download_to_filename(self, path: str) -> None:
        Path(path).write_bytes(self._store[self._key])

    def delete(self) -> None:
        del self._store[self._key]

    def generate_signed_url(self, expiration, method) -> str:  # noqa: ARG002
        return f"https://fake-signed-url.example/{self._key}"


class _FakeBucket:
    def __init__(self, store: dict):
        self._store = store

    def blob(self, key: str) -> _FakeBlob:
        return _FakeBlob(self._store, key)


@pytest.fixture()
def fake_gcs(monkeypatch):
    """A tiny in-memory stand-in for a GCS bucket, keyed exactly like the
    real one (the same relative_storage_path strings)."""
    store: dict[str, bytes] = {}
    monkeypatch.setattr(storage, "_gcs_bucket", lambda: _FakeBucket(store))
    return store


def test_local_backend_local_file_for_read_yields_existing_path_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "storage_backend", "local")
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path)

    relative = "company-a/documents/test.pdf"
    (tmp_path / "company-a" / "documents").mkdir(parents=True)
    (tmp_path / relative).write_bytes(b"%PDF-fake-content")

    with storage.local_file_for_read(relative) as path:
        assert path == tmp_path / relative
        assert path.read_bytes() == b"%PDF-fake-content"


def test_local_backend_generate_download_url_returns_none(monkeypatch):
    monkeypatch.setattr(storage.settings, "storage_backend", "local")
    assert storage.generate_download_url("company-a/documents/test.pdf") is None


def test_gcs_backend_local_file_for_read_downloads_and_cleans_up(monkeypatch, fake_gcs):
    monkeypatch.setattr(storage.settings, "storage_backend", "gcs")
    relative = "company-a/documents/test.pdf"
    fake_gcs[relative] = b"%PDF-fake-content-from-gcs"

    with storage.local_file_for_read(relative) as path:
        downloaded_path = path
        assert path.exists()
        assert path.read_bytes() == b"%PDF-fake-content-from-gcs"

    # Cleaned up (the NamedTemporaryFile is deleted) once the context exits --
    # this is what keeps a Cloud Run instance from silently accumulating
    # temp files across many document reads.
    assert not downloaded_path.exists()


def test_gcs_backend_generate_download_url_returns_a_url(monkeypatch, fake_gcs):
    monkeypatch.setattr(storage.settings, "storage_backend", "gcs")
    relative = "company-a/documents/test.pdf"
    fake_gcs[relative] = b"irrelevant"

    url = storage.generate_download_url(relative)
    assert url is not None
    assert relative in url


def test_delete_file_is_backend_agnostic_for_gcs(monkeypatch, fake_gcs):
    """This is the exact gap Bug-adjacent fix in document_service.py's
    upload_document() rollback path relies on: delete_file() (not
    resolve_path().unlink()) must actually remove a GCS blob, not silently
    no-op against a local path that was never written."""
    monkeypatch.setattr(storage.settings, "storage_backend", "gcs")
    relative = "company-a/documents/orphaned.pdf"
    fake_gcs[relative] = b"should be removed"

    storage.delete_file(relative)

    assert relative not in fake_gcs


def test_delete_file_on_gcs_does_not_raise_for_already_missing_blob(monkeypatch, fake_gcs):
    monkeypatch.setattr(storage.settings, "storage_backend", "gcs")
    storage.delete_file("company-a/documents/never-existed.pdf")  # must not raise

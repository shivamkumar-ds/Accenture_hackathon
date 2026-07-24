"""
Domain-level exceptions raised by the service layer.

Services never raise HTTPException directly — that would leak an API
concern into the business logic layer. Each API router is responsible
for catching these and mapping them to the appropriate HTTP response.
"""


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""


class ConflictError(Exception):
    """Raised when an operation would violate a uniqueness constraint."""


class AuthenticationError(Exception):
    """Raised when credentials are invalid, or a token/session is not valid."""


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file's type is not in the allowed set."""


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured maximum size."""


class ExtractionError(Exception):
    """Raised when the Capability Builder Agent cannot produce a valid extraction."""

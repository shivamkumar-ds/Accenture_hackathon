"""
Rate limiting — protects the endpoints that either create an account for
free (registration) or cost real money per call (document/tender upload,
capability build, decision evaluation), per RC-2 audit finding H-2:
`POST /auth/register` was fully open with no verification and no limiting,
so nothing stopped unlimited free account creation followed by immediate,
unbounded LLM spend.

In-memory storage, keyed by client IP — the simplest option that still
closes the concrete threat identified (unlimited free signup + unbounded
LLM-cost-endpoint access), and appropriate for the current single-instance
deployment. Per-user (rather than per-IP) limiting, and a shared store
(e.g. Redis) for a multi-instance deployment, are reasonable future
refinements — explicitly not required to close this finding, and
Redis specifically was one of the items this remediation pass was told
to leave alone.

`enabled=settings.rate_limit_enabled` (default True) exists purely so the
test suite can disable enforcement — see tests/conftest.py — without
touching any of the decorated route code.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

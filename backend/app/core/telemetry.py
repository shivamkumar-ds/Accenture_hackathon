"""
Minimal LLM-call telemetry sink — Phase A of the founder-approved
instrumentation-before-feature-work plan (see docs/CORE_ARCHITECTURE.md).

Deliberately thin: one function, one table (LLMCallEvent), no
dashboards, no aggregation. The goal is only "collect reliably from
day one" so the Bid Decision feature (and everything after it) has a
real baseline instead of a retrofit.

Lives in app/core/ rather than app/services/ because it's cross-cutting
infrastructure invoked from deep inside the agents/ layer (llm_client.py),
which has no request-scoped database session available to it. Opening a
short-lived session here — rather than threading a Session through every
agent function signature — keeps llm_client.py's existing signature
changes minimal, per the "thin layer" instruction.

Hard rule: a telemetry failure must never break the actual LLM call it's
describing. Every write is wrapped in try/except; failures are logged,
never raised.
"""

import logging
import uuid

from app.core.database import SessionLocal
from app.models import LLMCallEvent

logger = logging.getLogger(__name__)


def record_llm_call(
    *,
    purpose: str,
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
    success: bool,
    error_type: str | None = None,
    company_id: uuid.UUID | None = None,
    mission_id: uuid.UUID | None = None,
) -> None:
    db = SessionLocal()
    try:
        db.add(
            LLMCallEvent(
                purpose=purpose,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=success,
                error_type=error_type,
                company_id=company_id,
                mission_id=mission_id,
            )
        )
        db.commit()
    except Exception:
        # Telemetry is observational, never load-bearing -- a DB hiccup
        # here must not surface as (or be mistaken for) a real LLM
        # failure. Logged so it's still visible in the actual failure
        # case, just never raised.
        logger.warning("Failed to record LLM call telemetry (purpose=%s)", purpose, exc_info=True)
    finally:
        db.close()

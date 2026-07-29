"""
LLM call telemetry — Phase A instrumentation (see docs/CORE_ARCHITECTURE.md
Principle 3/8 and the founder-approved instrumentation-first sequencing).

One row per LLM call, written by app/core/telemetry.py from inside
llm_client.py's complete() implementations. Deliberately the only new
table for this phase: human-override events are already captured by the
existing AuditLog (approval_service.py's _log() calls), so no second
new table is needed for those — this file adds only what didn't already
exist anywhere.

Not a dashboard, not yet analyzed automatically — this is the "collect
reliably first" half of the instrumentation-before-feature-work plan.
company_id/mission_id are nullable because llm_client.py itself has no
request context; callers may enrich these later without a schema change.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class LLMCallEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "llm_call_events"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Which part of the pipeline made the call — capability_extraction,
    # tender_requirement_extraction, decision_matching, etc. Free text
    # rather than an enum deliberately: new call sites shouldn't require
    # a migration just to be tagged.
    purpose: Mapped[str] = mapped_column(String, default="unspecified")

    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)

    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)

    success: Mapped[bool] = mapped_column(Boolean)
    error_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Forward-looking, per CORE_ARCHITECTURE.md's caching-strategy section
    # -- not populated by anything yet, since no cache exists, but the
    # column exists now so a future cache layer doesn't need a migration
    # just to start reporting hit/miss here.
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluation_path: Mapped[str] = mapped_column(String, default="llm")

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    mission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True
    )

"""Pydantic schema for Mission."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import MissionStatus


class MissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    mission_type: str
    status: MissionStatus
    created_at: datetime
    completed_at: datetime | None
    recommendation_id: uuid.UUID | None
    capability_snapshot_id: uuid.UUID | None
    actual_outcome: str | None
    outcome_notes: str | None

    # Not columns on Mission itself -- Mission has no FK back to Tender.
    # Populated by the API layer (see missions.py's _attach_tender_info)
    # from the linked Tender row, so callers get the tender's real
    # human-readable identity instead of having to fall back to
    # mission_type, which is a fixed internal constant ("tender_evaluation"
    # for every mission), not a tender name. Defaulted to None so
    # MissionRead.model_validate(mission) still works untouched wherever
    # this enrichment isn't done (e.g. execute/archive action responses).
    tender_id: uuid.UUID | None = None
    tender_name: str | None = None


class ExecuteMissionRequest(BaseModel):
    """Optional body for POST /missions/{id}/execute. `provider` lets the
    caller pick which LLM engine runs the analysis for this mission.
    Restricted to "openai" for now -- get_llm_client() itself supports
    "gemini"/"qwen" too, but those aren't verified/usable in this
    deployment yet (see ADR-001 for qwen; gemini credentials aren't
    confirmed configured here), so the API only accepts the one option
    the frontend actually offers. Widening this Literal is the only
    change needed to expose another provider once it's verified.
    Omitted/null falls back to the server's configured default
    (settings.llm_provider), unchanged from before this field existed."""

    provider: Literal["openai"] | None = None

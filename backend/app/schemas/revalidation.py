"""Pydantic schemas for capability mutation (M9) and revalidation results."""

import uuid
from typing import Any

from pydantic import BaseModel


class CapabilityUpdateRequest(BaseModel):
    fields: dict[str, Any]


class RevalidationResult(BaseModel):
    entity_id: uuid.UUID
    changed_fields: list[str] = []
    affected_missions: list[str]
    new_recommendations: list[str]


class FreshnessSweepResult(BaseModel):
    missions_checked_affected: int
    new_recommendations: list[str]

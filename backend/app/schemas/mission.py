"""Pydantic schema for Mission."""

import uuid
from datetime import datetime

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

"""Mission and CapabilitySnapshot — 05_Database_Design.md."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import MissionStatus
from app.models.mixins import UUIDPrimaryKeyMixin


class Mission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "missions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    mission_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus, name="mission_status"), default=MissionStatus.CREATED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Snapshot & Recommendation linkage (recent schema update).
    # use_alter=True breaks the circular reference: CapabilitySnapshot and
    # Recommendation both reference missions.id, so these two FKs on
    # Mission are applied via a deferred ALTER TABLE, not at creation time.
    capability_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability_snapshots.id", use_alter=True, name="fk_missions_capability_snapshot_id"),
        nullable=True,
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", use_alter=True, name="fk_missions_recommendation_id"),
        nullable=True,
    )

    # Outcome tracking (recent schema update — enables Recommendation Accuracy, deferred until populated)
    actual_outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(String, nullable=True)


class CapabilitySnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "capability_snapshots"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String, nullable=True)

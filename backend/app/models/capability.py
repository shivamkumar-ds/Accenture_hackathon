"""
Capability entities — Certification, Employee, Project, Equipment, FinancialRecord.

All five inherit CapabilityMetadataMixin (created_at, updated_at,
last_verified_at, verification_status, confidence_score,
source_document_id) rather than repeating those six columns five times.
"""

import uuid
from datetime import date

from sqlalchemy import ARRAY, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import CapabilityMetadataMixin, UUIDPrimaryKeyMixin


class Certification(Base, UUIDPrimaryKeyMixin, CapabilityMetadataMixin):
    __tablename__ = "certifications"

    # index=True: every capability read/list/decision-matching query filters
    # by company_id (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    certification_name: Mapped[str] = mapped_column(String, nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Pre-existing fields, kept alongside the new Common Metadata fields
    # (see the duplication note given before this step) rather than merged.
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    source_document: Mapped[str | None] = mapped_column(String, nullable=True)


class Employee(Base, UUIDPrimaryKeyMixin, CapabilityMetadataMixin):
    __tablename__ = "employees"

    # index=True: every capability read/list/decision-matching query filters
    # by company_id (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    qualification: Mapped[str | None] = mapped_column(String, nullable=True)
    experience: Mapped[str | None] = mapped_column(String, nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Pre-existing field, kept alongside source_document_id — see duplication note.
    source_document: Mapped[str | None] = mapped_column(String, nullable=True)


class Project(Base, UUIDPrimaryKeyMixin, CapabilityMetadataMixin):
    __tablename__ = "projects"

    # index=True: every capability read/list/decision-matching query filters
    # by company_id (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    client: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    duration: Mapped[str | None] = mapped_column(String, nullable=True)
    completion_status: Mapped[str | None] = mapped_column(String, nullable=True)
    similarity_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)


class Equipment(Base, UUIDPrimaryKeyMixin, CapabilityMetadataMixin):
    __tablename__ = "equipment"

    # index=True: every capability read/list/decision-matching query filters
    # by company_id (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    equipment_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    specifications: Mapped[str | None] = mapped_column(String, nullable=True)


class FinancialRecord(Base, UUIDPrimaryKeyMixin, CapabilityMetadataMixin):
    __tablename__ = "financial_records"

    # index=True: every capability read/list/decision-matching query filters
    # by company_id (RC-1 audit finding B3) — unindexed until now.
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    financial_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    net_worth: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    working_capital: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    credit_rating: Mapped[str | None] = mapped_column(String, nullable=True)

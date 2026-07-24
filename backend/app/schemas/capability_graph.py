"""
Capability Graph response schemas (M4).

Each *GraphEntry combines its base Read schema with freshness fields via
straightforward multiple inheritance — five small classes, not a
generic wrapper abstraction, since each domain's own fields still need
to appear directly in the response (not nested under a sub-object) and
still need correct OpenAPI typing.
"""

from pydantic import BaseModel

from app.schemas.capability import (
    CertificationRead,
    EmployeeRead,
    EquipmentRead,
    FinancialRecordRead,
    ProjectRead,
)


class FreshnessFields(BaseModel):
    is_expired: bool
    is_stale: bool
    freshness_status: str  # "expired" | "stale" | "current"


class CertificationGraphEntry(CertificationRead, FreshnessFields):
    pass


class EmployeeGraphEntry(EmployeeRead, FreshnessFields):
    pass


class ProjectGraphEntry(ProjectRead, FreshnessFields):
    pass


class EquipmentGraphEntry(EquipmentRead, FreshnessFields):
    pass


class FinancialRecordGraphEntry(FinancialRecordRead, FreshnessFields):
    pass


class CapabilitySummary(BaseModel):
    """Derived from the entities in this response, not a stored value."""

    total_entities: int
    total_expired: int
    total_stale: int
    total_current: int
    by_domain: dict[str, int]


class CapabilityGraphResponse(BaseModel):
    summary: CapabilitySummary
    certifications: list[CertificationGraphEntry]
    employees: list[EmployeeGraphEntry]
    projects: list[ProjectGraphEntry]
    equipment: list[EquipmentGraphEntry]
    financial_records: list[FinancialRecordGraphEntry]

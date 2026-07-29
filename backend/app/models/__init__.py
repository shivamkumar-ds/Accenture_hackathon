"""
Importing this package registers every model with Base.metadata.

Anything that needs the full schema (Alembic autogenerate, app startup)
must import app.models, not an individual model module, or tables will
be silently missing from what SQLAlchemy knows about.
"""

from app.models.audit import AuditLog
from app.models.capability import Certification, Employee, Equipment, FinancialRecord, Project
from app.models.company import Company, User
from app.models.document import Document
from app.models.mission import CapabilitySnapshot, Mission
from app.models.recommendation import ComplianceMatrix, Recommendation
from app.models.telemetry import LLMCallEvent
from app.models.tender import CapabilityMapping, Requirement, Tender

__all__ = [
    "AuditLog",
    "Certification",
    "Employee",
    "Equipment",
    "FinancialRecord",
    "Project",
    "Company",
    "User",
    "Document",
    "CapabilitySnapshot",
    "Mission",
    "ComplianceMatrix",
    "Recommendation",
    "LLMCallEvent",
    "CapabilityMapping",
    "Requirement",
    "Tender",
]

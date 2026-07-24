"""
Enum value-sets for the BidOps schema.

Every enum here corresponds to a field the architecture documents named
but did not enumerate. See the explanation given alongside this
milestone step for the reasoning behind each set. None of these add new
fields or behavior — they type-constrain fields the frozen schema
already specifies.
"""

import enum


class UserRole(str, enum.Enum):
    ADMINISTRATOR = "administrator"
    EXECUTIVE = "executive"
    BID_MANAGER = "bid_manager"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class DocumentProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationStatus(str, enum.Enum):
    """Used by capability entities (Common Metadata)."""

    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REVIEW_REQUIRED = "review_required"


class ComplianceMatrixVerificationStatus(str, enum.Enum):
    """Used by Compliance Matrix rows specifically — distinct value set from capability VerificationStatus."""

    PENDING = "pending"
    VERIFIED_COMPLIANT = "verified_compliant"
    VERIFIED_NON_COMPLIANT = "verified_non_compliant"
    ESCALATED = "escalated"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequirementType(str, enum.Enum):
    ELIGIBILITY = "eligibility"
    TECHNICAL = "technical"
    CERTIFICATION = "certification"
    EXPERIENCE = "experience"
    EVALUATION_CRITERIA = "evaluation_criteria"
    DEADLINE = "deadline"
    SUBMISSION = "submission"


class MatchStatus(str, enum.Enum):
    """Used by both Capability Mapping and Compliance Matrix — same verdict vocabulary."""

    MET = "met"
    NOT_MET = "not_met"
    REVIEW_REQUIRED = "review_required"
    CONDITIONAL = "conditional"


class MissionStatus(str, enum.Enum):
    """Exactly the five states listed in 05_Database_Design.md's Mission Table."""

    CREATED = "created"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RecommendationType(str, enum.Enum):
    GO = "go"
    CONDITIONAL_GO = "conditional_go"
    REVIEW = "review"
    NO_GO = "no_go"


class CapabilityEntityType(str, enum.Enum):
    """Which of the five capability tables a Capability Mapping row points to."""

    CERTIFICATION = "certification"
    EMPLOYEE = "employee"
    PROJECT = "project"
    EQUIPMENT = "equipment"
    FINANCIAL_RECORD = "financial_record"

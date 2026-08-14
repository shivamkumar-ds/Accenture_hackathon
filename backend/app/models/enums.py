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


class AuthProvider(str, enum.Enum):
    """
    How a User authenticates (Phase 2: Google Authentication). LOCAL is the
    existing password_hash + bcrypt path, unchanged. GOOGLE means the user
    signs in exclusively via Google ID token verification -- password_hash
    is None for these accounts, never a random/unusable placeholder, so
    "this account has no password" is a real, queryable fact rather than
    an implied one.

    Deliberately a fact about the account, not a permission -- a GOOGLE
    account still goes through the exact same User row, company_id, role,
    and RBAC checks as a LOCAL account. This is what "integrated into the
    existing user model, not parallel auth logic" means in practice.
    """

    LOCAL = "local"
    GOOGLE = "google"


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


class BusinessDecision(str, enum.Enum):
    """
    The human's Business Decision on a mission (Bid Decision feature,
    docs/BID_DECISION_DESIGN.md) — deliberately a separate vocabulary
    from RecommendationType. RecommendationType is the AI's own output
    (what it recommends); BusinessDecision is what a human commits to
    after reading that recommendation. Collapsing these into one enum
    would blur "AI advises, human decides" into a single value the AI
    could be seen as choosing on the human's behalf.
    """

    PROCEED = "proceed"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ContactEmailStatus(str, enum.Enum):
    """
    Honest per-email delivery status for a ContactSubmission row (Contact
    Form Backend). Deliberately NOT a proxy for whether the submission
    itself succeeded -- the submission is durable the moment its DB row
    commits (see contact_service.submit_contact_form), independent of
    either email outcome. PENDING is the default set at insert time and
    is only ever a transient state within a single request (this is a
    synchronous send, not a queue) -- it exists so a row is never left
    with no status at all if the process crashes between the insert and
    the email attempt, matching the same PENDING-first convention as
    DocumentProcessingStatus/VerificationStatus elsewhere in this schema.
    SENT means the provider (Resend) accepted the message. FAILED covers
    every case where that didn't happen, including the provider not
    being configured at all (RESEND_API_KEY unset) -- both are equally
    "this email did not go out," and notification_error/confirmation_error
    on the model records which one it was.
    """

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class CapabilityEntityType(str, enum.Enum):
    """Which of the five capability tables a Capability Mapping row points to."""

    CERTIFICATION = "certification"
    EMPLOYEE = "employee"
    PROJECT = "project"
    EQUIPMENT = "equipment"
    FINANCIAL_RECORD = "financial_record"

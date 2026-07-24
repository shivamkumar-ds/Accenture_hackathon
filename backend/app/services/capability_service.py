"""
Capability service — the persistence layer for capability entities.

Owns the Document.processing_status lifecycle (PENDING -> PROCESSING ->
COMPLETED/FAILED) and translates agent-layer failures into the
established domain-exception pattern (ExtractionError), consistent with
every other service in this codebase.
"""

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.agents import capability_builder
from app.core import storage
from app.models import Certification, Employee, Equipment, FinancialRecord, Project
from app.models.enums import CapabilityEntityType, DocumentProcessingStatus, VerificationStatus
from app.services.document_service import get_document
from app.services.exceptions import ExtractionError

logger = logging.getLogger(__name__)

# Used only by build_capability_from_document (M3) — deliberately just
# the three MVP document types with an extraction agent. Do not add
# Equipment/FinancialRecord here; no agent exists for them yet.
ENTITY_MODELS = {
    CapabilityEntityType.CERTIFICATION: Certification,
    CapabilityEntityType.EMPLOYEE: Employee,
    CapabilityEntityType.PROJECT: Project,
}

# Used by the read/graph functions below (M4) — all five domains, since
# the capability graph represents the full company capability model
# even where a domain has no extraction agent yet and stays empty.
ALL_CAPABILITY_MODELS = {
    **ENTITY_MODELS,
    CapabilityEntityType.EQUIPMENT: Equipment,
    CapabilityEntityType.FINANCIAL_RECORD: FinancialRecord,
}

# Fields on the extraction result that need conversion before assignment
# to the SQLAlchemy model (date strings -> real dates). Everything else
# maps 1:1 by field name.
DATE_FIELDS = {"issue_date", "expiry_date"}


async def build_capability_from_document(
    db: Session,
    document_id: uuid.UUID,
    company_id: uuid.UUID,
    entity_type: CapabilityEntityType,
):
    # Raises NotFoundError (company-scoped) if the document doesn't
    # belong to this company — propagates as-is, the router already
    # knows how to map it to a 404.
    document = get_document(db, document_id, company_id)

    document.processing_status = DocumentProcessingStatus.PROCESSING
    db.commit()

    file_path = storage.resolve_path(document.storage_path)
    extension = file_path.suffix.lower()

    try:
        result = await capability_builder.build_capability(file_path, extension, entity_type)
    except Exception as exc:
        # Covers both document_parser failures and LLM call failures --
        # build_capability() calls both, and either can land here.
        logger.exception(
            "Capability extraction failed: document_id=%s entity_type=%s", document_id, entity_type.value
        )
        document.processing_status = DocumentProcessingStatus.FAILED
        document.processed_at = datetime.now(timezone.utc)
        db.commit()
        raise ExtractionError(f"Extraction failed for document '{document_id}': {exc}") from exc

    entity_fields = _prepare_fields(result.fields)
    model_cls = ENTITY_MODELS[entity_type]
    entity = model_cls(
        company_id=company_id,
        confidence_score=result.confidence_score,
        source_document_id=document.id,
        verification_status=VerificationStatus.PENDING,  # never auto-verified, regardless of confidence
        **entity_fields,
    )
    db.add(entity)

    document.processing_status = DocumentProcessingStatus.COMPLETED
    document.extraction_confidence = result.confidence_score
    document.processed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(entity)
    return entity_type, entity


def _prepare_fields(fields: dict) -> dict:
    prepared = dict(fields)
    for field_name in DATE_FIELDS:
        if field_name in prepared and prepared[field_name]:
            prepared[field_name] = date.fromisoformat(prepared[field_name])
    return prepared


def list_capabilities(db: Session, company_id: uuid.UUID) -> list[tuple[CapabilityEntityType, object]]:
    """
    Excludes soft-removed entities (removed_at IS NOT NULL) — this is the
    one shared function feeding both M4's capability graph view and
    M6/M9's matching candidate pool, so filtering here means a removed
    entity genuinely stops being considered everywhere at once, not just
    hidden from one view.
    """
    results: list[tuple[CapabilityEntityType, object]] = []
    for entity_type, model_cls in ALL_CAPABILITY_MODELS.items():
        rows = (
            db.query(model_cls)
            .filter(model_cls.company_id == company_id, model_cls.removed_at.is_(None))
            .all()
        )
        results.extend((entity_type, row) for row in rows)
    return results


def find_capability_by_id(
    db: Session, entity_id: uuid.UUID, company_id: uuid.UUID
) -> tuple[CapabilityEntityType, object] | None:
    """
    Deliberately NOT filtered by removed_at, unlike list_capabilities —
    PATCH/DELETE need to look up an entity regardless of its current
    removed state (e.g. to correctly report "already removed" on a
    second DELETE attempt), and a direct lookup by known ID is a
    different operation from browsing the active graph.
    """
    for entity_type, model_cls in ALL_CAPABILITY_MODELS.items():
        row = (
            db.query(model_cls)
            .filter(model_cls.id == entity_id, model_cls.company_id == company_id)
            .one_or_none()
        )
        if row is not None:
            return entity_type, row
    return None


# --- M9: plain capability mutation. No revalidation awareness here at
# all — that orchestration lives in revalidation_service.py, which calls
# these as pure CRUD, consistent with keeping this module focused on
# capability persistence only. ---

PATCHABLE_FIELDS = {
    CapabilityEntityType.CERTIFICATION: {
        "certification_name", "issuing_authority", "issue_date", "expiry_date", "status",
    },
    CapabilityEntityType.EMPLOYEE: {
        "name", "position", "qualification", "experience", "availability", "skills",
    },
    CapabilityEntityType.PROJECT: {
        "client", "industry", "contract_value", "duration", "completion_status", "similarity_tags",
    },
}


def update_capability_fields(entity_type: CapabilityEntityType, entity, updates: dict) -> dict:
    """
    Applies whitelisted field updates in-place (caller commits).
    Returns {field: (old_value, new_value)} for only the fields that
    genuinely changed — an update that resends identical values changes
    nothing and returns an empty dict, which is exactly what makes a
    repeated identical PATCH a real no-op upstream, not just a policy.
    """
    allowed = PATCHABLE_FIELDS.get(entity_type, set())
    unknown = set(updates.keys()) - allowed
    if unknown:
        raise ValueError(f"Field(s) not patchable for {entity_type.value}: {', '.join(sorted(unknown))}")

    changed = {}
    for field, new_value in updates.items():
        if field in DATE_FIELDS and isinstance(new_value, str):
            new_value = date.fromisoformat(new_value)
        old_value = getattr(entity, field)
        if old_value != new_value:
            changed[field] = (old_value, new_value)
            setattr(entity, field, new_value)
    return changed


def soft_remove_capability(entity) -> None:
    """Sets removed_at — caller is responsible for the 'already removed' conflict check."""
    entity.removed_at = datetime.now(timezone.utc)

"""
Capability Builder Agent.

Parses a document, builds the appropriate prompt, calls the LLM client,
validates the response, and computes a confidence score — returns a
plain result the service layer persists. This module never touches the
database directly (that's app/services/capability_service.py's job),
consistent with the AI Service Layer / Business Logic Layer separation
already established in the frozen architecture.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.agents.document_parser import ParsedDocument, extract_text
from app.agents.json_utils import parse_json_response
from app.agents.llm_client import get_llm_client
from app.agents.prompts import certification as certification_prompts
from app.agents.prompts import employee as employee_prompts
from app.agents.prompts import project as project_prompts
from app.models.enums import CapabilityEntityType
from app.schemas.extraction import CertificationExtraction, EmployeeExtraction, ProjectExtraction


@dataclass
class BuildResult:
    entity_type: CapabilityEntityType
    fields: dict
    confidence_score: float


PROMPT_MODULES = {
    CapabilityEntityType.CERTIFICATION: certification_prompts,
    CapabilityEntityType.EMPLOYEE: employee_prompts,
    CapabilityEntityType.PROJECT: project_prompts,
}

EXTRACTION_SCHEMAS = {
    CapabilityEntityType.CERTIFICATION: CertificationExtraction,
    CapabilityEntityType.EMPLOYEE: EmployeeExtraction,
    CapabilityEntityType.PROJECT: ProjectExtraction,
}

# Fields that must be present for the extraction to be considered
# usable at all — these map to NOT NULL columns on the target model.
# A null here isn't "low confidence", it's a failed extraction.
REQUIRED_FIELDS = {
    CapabilityEntityType.CERTIFICATION: ["certification_name"],
    CapabilityEntityType.EMPLOYEE: ["name"],
    CapabilityEntityType.PROJECT: [],
}


async def build_capability(
    file_path: Path, extension: str, entity_type: CapabilityEntityType
) -> BuildResult:
    # RC-1 audit finding E1: extract_text()'s OCR fallback path shells out
    # to Poppler (pdf2image.convert_from_path) and Tesseract
    # (pytesseract.image_to_string/image_to_data) and blocks until both
    # return -- multiple seconds for a scanned multi-page document.
    # asyncio's event loop is single-threaded, so calling this directly
    # from an async def coroutine would freeze every other concurrent
    # request (any user's) for that entire duration. asyncio.to_thread
    # moves it off the event loop.
    parsed = await asyncio.to_thread(extract_text, file_path, extension)
    if not parsed.text.strip():
        raise ValueError(
            "No extractable text found in document (parsing and OCR both produced empty output)."
        )

    prompt_module = PROMPT_MODULES[entity_type]
    user_prompt = prompt_module.build_prompt(parsed.text)

    client = get_llm_client()
    raw_response = await client.complete(prompt_module.SYSTEM_PROMPT, user_prompt, purpose="capability_extraction")

    extracted_json = parse_json_response(raw_response)
    schema_cls = EXTRACTION_SCHEMAS[entity_type]
    validated = schema_cls.model_validate(extracted_json)
    fields = validated.model_dump()

    for required_field in REQUIRED_FIELDS[entity_type]:
        if not fields.get(required_field):
            raise ValueError(
                f"Extraction did not find required field '{required_field}' — "
                f"treating as a failed extraction rather than persisting an incomplete record."
            )

    # Even entity types with no single named-required field (Project) still
    # need at least one populated field — an entirely empty record isn't a
    # meaningful extraction, even though every Project column is nullable
    # at the database level.
    if not any(value not in (None, "", []) for value in fields.values()):
        raise ValueError(
            "Extraction found no populated fields at all — "
            "treating as a failed extraction rather than persisting an empty record."
        )

    confidence = _compute_confidence(parsed, fields, list(schema_cls.model_fields.keys()))
    return BuildResult(entity_type=entity_type, fields=fields, confidence_score=confidence)


def _compute_confidence(parsed: ParsedDocument, fields: dict, expected_fields: list[str]) -> float:
    """
    Derived from concrete signals, not an LLM self-report: OCR word-level
    confidence when OCR was used, a high fixed baseline when native text
    extraction succeeded, scaled down by how many expected fields actually
    came back populated.
    """
    if parsed.used_ocr and parsed.ocr_confidence is not None:
        base = parsed.ocr_confidence / 100.0
    else:
        base = 0.95

    populated = sum(1 for field in expected_fields if fields.get(field) not in (None, "", []))
    completeness = populated / len(expected_fields) if expected_fields else 1.0

    return round(base * completeness, 4)

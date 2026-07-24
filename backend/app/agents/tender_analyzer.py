"""
Tender Analysis Agent.

Pipeline: parse pages -> chunk by page count -> LLM extraction per
chunk (page-marked, for provenance) -> deterministic duplicate removal
-> validate -> return structured requirements. Persistence is
tender_service.py's job, consistent with the AI Service Layer /
Business Logic Layer separation already established (M3 follows the
same split).

Deliberately narrow: this module only knows how to analyze tenders. No
generic "document chunking framework" — Certifications/CVs (M3) are
short enough to never need chunking, so this logic doesn't try to serve
both use cases.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.agents.document_parser import extract_pdf_pages
from app.agents.json_utils import parse_json_response
from app.agents.llm_client import get_llm_client
from app.agents.prompts import tender_requirement
from app.core.config import get_settings
from app.schemas.extraction import ExtractedRequirement, TenderChunkExtraction

settings = get_settings()


@dataclass
class RequirementResult:
    requirement_type: str
    description: str | None
    mandatory: bool
    source_page: int | None
    confidence: float


async def analyze_tender(file_path: Path) -> list[RequirementResult]:
    # RC-1 audit finding E1: extract_pdf_pages() is a synchronous, CPU-bound
    # call (pypdf parsing over a potentially large multi-page tender). Run
    # off the event loop via asyncio.to_thread so a single upload can't
    # stall every other concurrent request for the duration of the parse.
    pages = await asyncio.to_thread(extract_pdf_pages, file_path)
    if not pages:
        raise ValueError("Tender document has no pages.")
    if not any(page.strip() for page in pages):
        raise ValueError(
            "No extractable text found on any page (scanned/image-only tenders are "
            "out of scope for M5 — OCR is not applied to tender documents)."
        )

    chunk_size = settings.tender_chunk_page_size
    all_requirements: list[ExtractedRequirement] = []
    page_had_text: dict[int, bool] = {}

    client = get_llm_client()

    for chunk_start in range(0, len(pages), chunk_size):
        chunk_pages = {
            page_num + 1: pages[page_num]
            for page_num in range(chunk_start, min(chunk_start + chunk_size, len(pages)))
        }
        for page_num, text in chunk_pages.items():
            page_had_text[page_num] = bool(text.strip())

        user_prompt = tender_requirement.build_prompt(chunk_pages)
        raw_response = await client.complete(tender_requirement.SYSTEM_PROMPT, user_prompt)

        extracted_json = parse_json_response(raw_response)
        validated = TenderChunkExtraction.model_validate(extracted_json)
        all_requirements.extend(validated.requirements)

    deduplicated = _deduplicate(all_requirements)
    return [_to_result(req, page_had_text) for req in deduplicated]


def _deduplicate(requirements: list[ExtractedRequirement]) -> list[ExtractedRequirement]:
    """
    Deterministic duplicate removal: exact match on (requirement_type,
    normalized description) — not fuzzy/semantic matching. Keeps the
    first occurrence (lowest source_page). The same requirement can
    legitimately appear verbatim in more than one section of a real
    tender (e.g. a summary section repeating a detailed requirement);
    this only removes true exact duplicates, not similar-but-distinct ones.
    """
    seen: set[tuple[str, str]] = set()
    result = []
    for req in requirements:
        key = (req.requirement_type, (req.description or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(req)
    return result


def _to_result(req: ExtractedRequirement, page_had_text: dict[int, bool]) -> RequirementResult:
    """
    Confidence from measurable signals, consistent with M3's philosophy
    (never an LLM self-report): whether the source page actually had
    native text (vs. an empty page somehow yielding a match — a red
    flag, not a confident result), scaled by field completeness.
    """
    page_ok = req.source_page is not None and page_had_text.get(req.source_page, False)
    base = 0.95 if page_ok else 0.3

    fields = [req.requirement_type, req.description, req.source_page]
    populated = sum(1 for f in fields if f not in (None, ""))
    completeness = populated / len(fields)

    confidence = round(base * completeness, 4)
    return RequirementResult(
        requirement_type=req.requirement_type,
        description=req.description,
        mandatory=req.mandatory,
        source_page=req.source_page,
        confidence=confidence,
    )

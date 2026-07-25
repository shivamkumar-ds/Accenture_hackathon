"""
Heuristic (regex-only, no LLM call) guesses for a tender's name,
issuing organization, and closing date from the first page or two of
its PDF text -- purely to prefill the New Tender upload form before
the user commits. Never persisted, never blocks upload, and every
field can legitimately come back None: real procurement documents
don't share one universal layout, so this only recognizes common,
explicit label patterns ("Tender Name:", "Government of X",
"Closing Date:", etc.) rather than pretending to understand the
document. Same honesty posture as mock_extraction.py -- genuinely
reading real text, not fabricating plausible-looking values when
nothing is actually found.
"""

import re
from datetime import date, datetime

TENDER_NAME_PATTERNS = [
    r"(?:Tender|Project|Work)\s*Name\s*[:\-]\s*(.+)",
    r"Name\s+of\s+(?:the\s+)?(?:Tender|Work|Project)\s*[:\-]\s*(.+)",
    r"Subject\s*[:\-]\s*(.+)",
]

ORGANIZATION_LINE_PATTERNS = [
    r"^\s*(Government\s+of\s+[A-Za-z.,&\- ]+)\s*$",
    r"^\s*(Ministry\s+of\s+[A-Za-z.,&\- ]+)\s*$",
    r"^\s*(Department\s+of\s+[A-Za-z.,&\- ]+)\s*$",
]
ORGANIZATION_LABEL_PATTERNS = [
    r"(?:Issuing\s*Authority|Organi[sz]ation|Department|Client)\s*[:\-]\s*(.+)",
]

DATE_LABEL_PATTERNS = [
    r"(?:Closing\s*Date|Last\s*Date(?:\s*for\s*Submission)?|Due\s*Date|"
    r"Submission\s*Deadline|Bid\s*Submission\s*(?:End\s*)?Date)\s*[:\-]?\s*"
    r"([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})"
]

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"]


def _first_match(text: str, patterns: list[str], flags=re.IGNORECASE) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            candidate = match.group(1).strip().splitlines()[0].strip(" .,:-")
            if candidate:
                return candidate[:200]
    return None


def _guess_organization(text: str) -> str | None:
    line_match = _first_match(text, ORGANIZATION_LINE_PATTERNS, re.IGNORECASE | re.MULTILINE)
    if line_match:
        return line_match
    return _first_match(text, ORGANIZATION_LABEL_PATTERNS)


def _guess_closing_date(text: str) -> date | None:
    for pattern in DATE_LABEL_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1)
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def guess_metadata(text: str) -> dict:
    return {
        "tender_name": _first_match(text, TENDER_NAME_PATTERNS),
        "organization": _guess_organization(text),
        "closing_date": _guess_closing_date(text),
    }

"""Shared LLM-response utilities — used by both capability_builder.py and tender_analyzer.py."""

import json
import re


def parse_json_response(raw: str) -> dict:
    """Models sometimes wrap JSON in markdown fences despite instructions not to — strip if present."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned)
    return json.loads(cleaned.strip())

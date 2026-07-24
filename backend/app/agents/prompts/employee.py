"""Prompt for extracting structured data from an employee CV."""

SYSTEM_PROMPT = (
    "You are extracting structured data from an EMPLOYEE CV document. "
    "Return ONLY valid JSON matching the requested schema — no markdown "
    "fences, no explanation, no extra text. Use null for any field you "
    "cannot find in the document."
)


def build_prompt(document_text: str) -> str:
    return f"""Extract the following fields from this CV and return ONLY this JSON shape:

{{
  "name": string or null,
  "position": string or null,
  "qualification": string or null,
  "experience": string or null,
  "availability": string or null,
  "skills": array of strings or null
}}

Document text:
\"\"\"
{document_text}
\"\"\"
"""

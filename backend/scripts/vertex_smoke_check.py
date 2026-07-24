"""
Vertex AI infrastructure smoke test -- a developer utility, NOT a pytest
test file (deliberately not named test_*.py, and lives under scripts/,
outside anything pytest.ini points at) so it is never auto-collected or
auto-run by `pytest` in CI. Running it always requires real GCP
credentials (ADC), which CI never has and never should.

Purpose: isolate "is the cloud infrastructure working" from "is the
BidOps backend working." If this script fails, the problem is Vertex
AI / IAM / ADC configuration, not GeminiClient or business logic --
if this script passes but GeminiClient still fails, the problem is in
the application layer instead.

Usage (from the BidOps backend venv, with ADC already configured via
`gcloud auth application-default login --impersonate-service-account=...`):

    python scripts/vertex_smoke_test.py

Requires GOOGLE_CLOUD_PROJECT to be set (env var or .env) -- does not
read BidOps's own Settings class, deliberately: this script must keep
working even if app.core.config changes shape, since its whole point is
to be a debugging layer independent of the application.
"""

import os
import sys

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "bidops-ai")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def check_plain_text() -> bool:
    print(f"[1/2] Plain text call (project={PROJECT_ID}, location={LOCATION})...")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    response = client.models.generate_content(
        model=MODEL,
        contents="Say hello and confirm you are responding via Vertex AI.",
    )
    print(f"    -> {response.text!r}")
    return bool(response.text)


def check_structured_json() -> bool:
    print("[2/2] Structured JSON call (representative of real pipeline usage)...")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    response_schema = {
        "type": "object",
        "properties": {
            "requirement": {"type": "string"},
            "match_status": {"type": "string", "enum": ["MATCHED", "NOT_MATCHED", "PARTIAL"]},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["requirement", "match_status", "confidence", "reasoning"],
    }
    response = client.models.generate_content(
        model=MODEL,
        contents=(
            "A tender requires: 'Vendor must hold a valid ISO 27001 certification.' "
            "The vendor's capability record shows: 'ISO 27001:2013 certified, valid until 2027.' "
            "Evaluate whether this requirement is matched."
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    print(f"    -> {response.text}")
    return bool(response.text)


def main() -> int:
    try:
        ok_text = check_plain_text()
        ok_json = check_structured_json()
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: this is a
        # standalone debugging script, not application code bound by the
        # narrow-exception discipline in llm_client.py.
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1

    if ok_text and ok_json:
        print("SUCCESS -- Vertex AI infrastructure verified independently of BidOps backend.")
        return 0

    print("FAILED -- one or both calls returned an empty response.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

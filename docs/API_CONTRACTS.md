# BidOps API Contracts

Concise developer reference for the core public endpoints — what to send, what comes back,
and why. This is a companion to the OpenAPI spec (served at `/docs` / `/openapi.json` by the
running app), not a replacement for it: it exists so a developer (or an AI agent working in
this codebase) can understand the five endpoints a client actually needs without running the
server first. For every field, type, and validation rule, the OpenAPI spec and the Pydantic
schemas under `backend/app/schemas/` remain the source of truth — if this document and the
code ever disagree, the code is right and this document is stale and should be corrected.

All endpoints are mounted under `/api/v1`. All request/response bodies are JSON except file
upload, which is `multipart/form-data`.

## Authentication

Every endpoint below Authentication requires a bearer token: `Authorization: Bearer <token>`.
Missing or invalid tokens return `401`; a valid token for the wrong role returns `403`
(see `99_DECISIONS_LOG.md` B-002 for why those two are deliberately distinguished).

### `POST /api/v1/auth/register`

Creates a brand-new Company and its first Administrator user together — the only endpoint
that creates a company from nothing. Returns `201`.

Request (`RegisterRequest`):
```json
{
  "company_name": "string",
  "industry": "string | null",
  "registration_number": "string",
  "country": "string | null",
  "admin_name": "string",
  "admin_email": "user@example.com",
  "admin_password": "string, min 8 chars"
}
```

Response (`TokenResponse`, `201`):
```json
{
  "access_token": "string (JWT)",
  "token_type": "bearer",
  "user": { "id": "uuid", "company_id": "uuid", "name": "string", "email": "string",
            "role": "administrator", "status": "active", "created_at": "datetime" }
}
```
`409` if `registration_number` or `admin_email` already exists.

### `POST /api/v1/auth/login`

Request (`LoginRequest`): `{"email": "user@example.com", "password": "string"}`
Response: same `TokenResponse` shape as register. `401` on bad credentials.

### `GET /api/v1/auth/profile`

No body. Returns the caller's own `UserRead` (same shape as `TokenResponse.user` above).

---

## Tender Upload — `POST /api/v1/tenders/upload`

Uploads a tender document, creates the `Tender` row, and creates an inert `Mission` row
alongside it (`mission_type="tender_evaluation"`, `status="created"`) — no analysis runs yet;
call Mission Execute (below) to actually run it. Returns `201`.

Request: `multipart/form-data`
| field | type | required |
|---|---|---|
| `file` | file | yes |
| `tender_name` | string | no |
| `organization` | string | no |
| `closing_date` | date (`YYYY-MM-DD`) | no |

Response (`TenderUploadResult`, added Milestone 6 — see `99_DECISIONS_LOG.md` D-144):
```json
{ "tender_id": "uuid", "mission_id": "uuid" }
```
Use `mission_id` to call `POST /missions/{mission_id}/execute` next — this is the intended,
correct next step for a client, not `GET /tenders/{tender_id}` directly.

---

## Capability Build — `POST /api/v1/capabilities/build`

Runs the Capability Builder agent against an already-uploaded document, extracting one
structured capability entity. Returns `201`. Only three entity types are supported as of
this milestone — `equipment` and `financial_record` exist in the schema/graph but have no
extraction agent yet and will return `422` if requested here.

Request (`BuildCapabilityRequest`):
```json
{ "document_id": "uuid", "entity_type": "certification" }
```
`entity_type` ∈ `certification | employee | project` (requesting `equipment` or
`financial_record` returns `422`).

Response (`CapabilityBuildResult`, added Milestone 6 — see `99_DECISIONS_LOG.md` D-144):
```json
{ "entity_type": "certification", "entity": { "...fields specific to entity_type..." } }
```
`entity`'s shape depends on `entity_type`: `CertificationRead`, `EmployeeRead`, or
`ProjectRead` (see `backend/app/schemas/capability.py`) — all three share a common base
(`id`, `company_id`, `confidence_score`, `source_document_id`, `verification_status`,
`last_verified_at`, `removed_at`, `created_at`) plus type-specific fields (e.g.
`certification_name`/`issuing_authority` for a certification, `name`/`skills` for an
employee, `client`/`contract_value` for a project).

To read the full capability graph afterward (all entities, grouped, with computed freshness),
use `GET /api/v1/capabilities` (`CapabilityGraphResponse`) — a separate, already-typed
endpoint, not documented further here since it isn't one of the five in scope for this file.

---

## Mission Execute — `POST /api/v1/missions/{mission_id}/execute`

The Mission Orchestrator's single entry point: runs Tender Analysis (if not already
`completed`) followed by Decision Intelligence (if the mission isn't already past that stage),
in order, idempotently — re-executing an already-completed mission is a safe no-op, not a
duplicate run (see D-126/D-127 for the exact staging rules). No request body.

Response (`MissionRead`, `200`):
```json
{
  "id": "uuid", "company_id": "uuid", "user_id": "uuid",
  "mission_type": "tender_evaluation",
  "status": "created | running | awaiting_approval | completed | archived",
  "created_at": "datetime", "completed_at": "datetime | null",
  "recommendation_id": "uuid | null", "capability_snapshot_id": "uuid | null",
  "actual_outcome": "string | null", "outcome_notes": "string | null"
}
```
A successful run leaves `status` at `awaiting_approval` with `recommendation_id` populated —
call Decision Recommendation (below) to see what was actually decided.

Errors: `404` unknown mission, `409` mission already `running` (duplicate-execution guard,
D-127), `422` extraction failure (e.g. malformed LLM output on every retry for some chunk).

---

## Decision Recommendation — `GET /api/v1/recommendations/{mission_id}`

Returns the current recommendation bundle for a mission — safe to call any time after at
least one successful Mission Execute. (`GET /api/v1/evaluation/{mission_id}` is a second,
intentionally identical endpoint — both exist because the frozen API spec named them
separately with no principled difference found; see D-121.)

Response (`EvaluationResponse`, `200`):
```json
{
  "recommendation": {
    "id": "uuid", "mission_id": "uuid",
    "recommendation_type": "go | conditional_go | review | no_go",
    "executive_summary": "string | null", "risk_level": "low | medium | high | critical | null",
    "generated_at": "datetime",
    "document_confidence": "float | null", "entity_confidence": "float | null",
    "matching_confidence": "float | null", "recommendation_confidence": "float | null",
    "overall_confidence": "float | null",
    "snapshot_id": "uuid | null"
  },
  "compliance_matrix": [
    {
      "id": "uuid", "requirement_id": "uuid",
      "status": "met | not_met | review_required | conditional",
      "supporting_evidence": "string | null", "notes": "string | null",
      "requires_verification": "bool", "verification_reason": "string | null",
      "risk_level": "low | medium | high | critical | null",
      "verification_status": "pending | verified_compliant | verified_non_compliant | escalated",
      "matching_confidence": "float | null", "evidence_reference": "uuid | null"
    }
  ],
  "gap_analysis": [
    {
      "requirement_id": "uuid", "requirement_type": "eligibility | technical | certification | experience | evaluation_criteria | deadline | submission",
      "description": "string | null", "mandatory": "bool",
      "status": "met | not_met | review_required | conditional", "reason": "string | null"
    }
  ]
}
```
`gap_analysis` is computed at response time from `compliance_matrix` (every row whose status
isn't `met`) — not a stored table, so it always reflects the same data as `compliance_matrix`
in the same response, never a separate source of truth.

A mission may accumulate more than one `Recommendation` over time (M9 revalidation creates a
new one rather than overwriting) — `GET /missions/{mission_id}/recommendations` (plural,
different endpoint, not detailed here) returns the full history; this endpoint always returns
whichever one `Mission.recommendation_id` currently points to.

To record a human decision against this recommendation, see
`POST /api/v1/approval` (`ApprovalDecisionRequest` → `MissionRead`) — outside this file's
scope but immediately downstream of this endpoint.

---

## Conventions that apply across all endpoints above

- Every list/read endpoint scopes results to the caller's own `company_id` — cross-tenant
  access returns `404`, never `403`, so existence of another company's data is never
  revealed (established from M1 onward, reaffirmed for the one endpoint that didn't follow
  it — see B-006).
- Timestamps are ISO 8601 (`datetime`); IDs are UUIDv4 strings.
- Validation errors (malformed request body) return FastAPI's native `422` with a `detail`
  array — no custom envelope (see D-108: the documented `{success, data}` envelope was
  deliberately not built).
- This document covers the five endpoint groups the founder asked for explicitly. It is not
  a full API reference — for every other endpoint (documents, users, company, capability
  graph/mutation, compliance verification, approval history), read the route file directly
  under `backend/app/api/v1/` or the live OpenAPI spec.

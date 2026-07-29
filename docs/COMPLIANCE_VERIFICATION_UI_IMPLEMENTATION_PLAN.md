# Compliance Verification UI — Implementation Plan (No Code)

Status: **Plan only — no code written.** Follows `docs/COMPLIANCE_VERIFICATION_UI_NOTE.md`'s six answers, revised after a design discussion (see "Amendments" at the bottom) that changed five things before any code was written: row-expansion state moved to be local per row, the blocking calculation reframed as a UI-only readiness indicator with no duplicated business rule, the Verify button gated on mission status, and — the one real scope change — a small additive backend schema addition to expose the complete verification metadata (`verified_by`, `verified_by_name`, `verified_at`) in one shot rather than growing the API field-by-field later.

## Goal

Implement the missing frontend workflow for compliance verification using the existing backend API (`POST /compliance/{id}/verify`, already live and tested — see `backend/app/services/approval_service.py:69-109`).

**No database changes. No migrations. No new endpoints. No authorization changes. No business-logic changes.** One additive backend response-schema change (see Amendments) — everything else is frontend-only.

---

## Files to be Modified

### `frontend/src/pages/Evaluation.tsx` (currently 532 lines)

**Reason:** The Compliance Matrix and `MatrixRow` component already live here — this is the only place a human sees a row's requirement, status, risk, and evidence trail together. Splitting verification into a separate file would break that "one row, one place to decide" flow.

**Changes:**
- `MatrixRow`: add a "Verify" action + inline expand form (status choice + optional note + confirm), shown when `entry.requires_verification` is true; on success, replace with a "Verified" badge + "Change verification" link.
- New local component `VerificationForm` (or inlined — see Components Affected) for the three-way status choice + note + confirm/cancel.
- `BusinessDecisionPanel`: add a blocking-rows banner + disable Save when any HIGH/CRITICAL `requires_verification` row is unverified (client-side precomputation of what the backend's `get_blocking_rows()` already checks server-side).

**Approx:** +130 to +160 LOC (mostly in `MatrixRow` and the new inline form; `BusinessDecisionPanel` changes are small — one `useMemo` + one conditional banner + one extra `disabled` condition).

### `frontend/src/api/endpoints.ts` (currently 155 lines)

**Reason:** No compliance-verify call exists yet.

**Changes:** One new function, `verifyComplianceRow(complianceId, payload)`, calling the already-existing `POST /compliance/{id}/verify`. `getApprovalHistory()` (already present, currently unused) stays unused — this feature doesn't need it, per the Design Note's "minimal audit trail" answer.

**Approx:** +6 LOC.

### `frontend/src/api/types.ts` (currently 306 lines)

**Reason:** `VerifyComplianceRequest` (request shape) doesn't exist on the frontend yet; `ComplianceMatrixEntryRead` (response shape, already present at `frontend/src/api/types.ts:201-217`) needs no changes — it already carries every field this feature reads (`requires_verification`, `verification_status`, `risk_level`, `verified_by`... — checking: `verified_by`/`verified_at` are **not currently on this type**, only on the backend model, so those two fields need to be added since the "Verified by/when" badge needs them).

**Changes:** New `VerifyComplianceRequest` interface (`verification_status`, `note`); add `verified_by: string | null` and `verified_at: string | null` to `ComplianceMatrixEntryRead`.

**Approx:** +10 LOC.

### `frontend/src/components/kit/Badge.tsx` (currently 66 lines)

**Reason:** `semanticTone` (line 17-23) has no entries for `verified_compliant`, `verified_non_compliant`, or `escalated` — the three real values `ComplianceMatrixVerificationStatus` can take (excluding `pending`, already mapped). Without this, the verified-status badge would silently fall back to neutral gray for all three, losing the compliant/non-compliant/escalated distinction the whole feature exists to show.

**Changes:** Three new keys in `semanticTone` (`verified_compliant: "success"`, `verified_non_compliant: "danger"`, `escalated: "warning"`).

**Approx:** +3 LOC.

---

## Components Affected

| Component | Modified? | New? | Deleted? | Refactored? |
|---|---|---|---|---|
| `Evaluation.tsx` (page) | Yes | No | No | No |
| `MatrixRow` | Yes | No | No | No |
| `BusinessDecisionPanel` | Yes | No | No | No |
| `VerificationForm` (inline form for status + note) | No | Yes | No | No |
| `api/endpoints.ts` | Yes | No | No | No |
| `api/types.ts` | Yes | No | No | No |
| `components/kit/Badge.tsx` | Yes | No | No | No |

No component is deleted or refactored — every change is additive to an existing file.

---

## API Calls

| Endpoint | Reused / New / Removed |
|---|---|
| `POST /compliance/{id}/verify` | **Reused** — already implemented, already tested server-side, zero changes. |
| `GET /evaluation/{missionId}` | **Reused** — already the page's data source; `ComplianceMatrixEntryRead` in its response already carries the fields this feature needs (plus the two additions noted above). |
| `GET /approval/{mission_id}` | **Not used** — deliberately, per the Design Note's "minimal audit trail" decision. Stays defined but uncalled, exactly as it is today. |

**No new endpoints. No removed endpoints.**

---

## State Changes

New React state, all local to `Evaluation.tsx`:

- `verifyingRowId: string | null` — which compliance row currently has its inline form expanded (only one open at a time, same pattern as the existing `expanded` status-group state).
- `verificationDraft: { status: ComplianceMatrixVerificationStatus; note: string } | null` — the in-progress form values for whichever row is open.
- `savingVerification: boolean` — disables the confirm button / shows a spinner during the API call.

`blockingRows` is **not new state** — it's a derived `useMemo` computed from `data.compliance_matrix` (already in state), not a separate piece of state to keep in sync.

Nothing else. No new global/context state, no new state in any other page.

---

## UI Changes

**Matrix Row — before:**
```
[Requirement text]                    [mandatory] [risk] [92% match]
> View evidence trail
```

**Matrix Row — after (row requires verification, unverified):**
```
[Requirement text]                    [mandatory] [risk] [92% match]
> View evidence trail
[Verify ▾]
```//clicking Verify expands:
```
  ( ) Verified Compliant   ( ) Verified Non-Compliant   ( ) Escalated
  [ note textarea, optional ]
  [Cancel]  [Confirm]
```

**Matrix Row — after (verified):**
```
[Requirement text]                    [mandatory] [risk] [92% match]
> View evidence trail
[Verified Compliant] · by you · 2 min ago   [Change verification]
```

**Business Decision panel — new banner (only when blocking rows exist):**
```
⚠ 2 item(s) must be verified before you can save a decision.
  [Save Decision]  <- disabled
```

---

## Business Decision Changes

**Old:** Save button disabled only when `mission.status !== "awaiting_approval"`.

**New:** Save button disabled when `mission.status !== "awaiting_approval"` **OR** `blockingRows.length > 0` (client-side mirror of the backend's existing `get_blocking_rows()` check — not a new rule, just surfaced before the click instead of after a 409).

No change to what decisions do once saved, no change to the state-transition table in `BID_DECISION_DESIGN.md` §5.

---

## Error Handling

| Case | Handling |
|---|---|
| `403` (unauthorized — not Executive/Administrator) | Toast, via existing `extractErrorMessage` pattern. Form stays open so the user doesn't lose their note. |
| `409` (mission no longer `awaiting_approval` — e.g. someone else just recorded a decision) | Toast + refetch the mission/evaluation so the UI reflects the real current state, same pattern already used in `handleRun`. |
| `422` (validation — e.g. `PENDING` submitted, which the backend schema already rejects) | Shouldn't be reachable from the UI at all, since the three exposed choices never include `PENDING` — defensive toast only, not expected in practice. |
| `500` / network error | Toast via `extractErrorMessage`, same as every other write call in this app. Row stays in its pre-submit state, nothing is optimistically updated before the response returns. |

No retry logic beyond the user manually clicking Confirm again — consistent with every other action in this codebase (no existing write path has automatic retry).

---

## Testing Impact

**Existing tests:** None break. `tests/test_bid_decision.py` already tests `record_decision()`'s blocking-row behavior at the service layer (`TestBlockingComplianceRows`, 2 tests) — that logic isn't touched by this frontend-only change. No backend file changes in this plan, so the backend test suite is unaffected by definition.

**New tests needed:**
- **Backend:** None — no backend behavior changes.
- **Frontend:** No automated frontend test suite currently exists in this repo (confirmed: no `*.test.tsx`/`*.spec.tsx` files, no test runner configured in `package.json`) — consistent with how every other frontend feature shipped so far in this project has been verified (manual + `tsc --noEmit` + `vite build`), not a gap introduced by this feature.
- **Manual:** (1) verify a row as each of the three statuses, confirm badge + backend `AuditLog` entry; (2) verify a HIGH/CRITICAL row, confirm the Business Decision banner clears and Save re-enables; (3) attempt Save with a blocking row still unverified, confirm banner + disabled state (never reaches the 409, by design); (4) re-verify an already-verified row, confirm it overwrites (per the Design Note's "undo via re-verify" answer); (5) verify as a non-Executive/Administrator user, confirm 403 toast.

---

## Accessibility

- **Keyboard:** Verify button and the three status choices are real `<button>`/`<input type="radio">` elements (not `div onClick`), so they're natively tab-reachable and activatable with Enter/Space — same convention already used by `DECISION_OPTIONS` in `BusinessDecisionPanel` (`Evaluation.tsx:485-497`).
- **Focus:** Opening the inline form moves focus to the first status option; closing (Cancel or successful Confirm) returns focus to the row's Verify button, so keyboard users aren't dropped at the top of the page.
- **Disabled buttons:** Save button's disabled state gets a `title`/`aria-describedby` explaining *why* (blocking rows vs. wrong mission status) rather than a silent disable — same gap-avoidance the existing `Button` component already supports via native `disabled`.
- **ARIA:** Verified-status badge gets `role="status"` text equivalent to its color (compliant/non-compliant/escalated) so the distinction isn't color-only — matches this codebase's existing `Badge` component, which already always pairs color with a text label, never color alone.

---

## Out of Scope

Explicitly **not** doing, this feature or later without a separate approval:

- Bulk verify (verify multiple rows in one action).
- A dedicated history/timeline page for `decision_events` (data already exists via `GET /approval/{mission_id}`, per the Design Note — not built here).
- Notifications/alerts when a row needs verification.
- Any change to who can verify (`require_approver` stays exactly as it is — Executive/Administrator).
- Any backend change of any kind — model, schema, service, route, or migration.

---

## Risk Assessment

| Area | Risk | Why |
|---|---|---|
| Business Decision (Phase B, just shipped) | Low, positive | This closes the exact gap the conformance review found — makes the existing blocking-row gate reachable instead of a dead end. No change to `record_decision()`'s own logic. |
| Evaluation page | Low | Additive only — existing `MatrixRow` rendering, filtering, and grouping logic is unchanged; verification state is new, layered on top. |
| Reports | None | Reports.tsx is not touched by this plan. |
| Backend API | None | Zero backend files in this plan's file list. |
| Regression surface | Low | The only shared file touched outside `Evaluation.tsx` itself is `Badge.tsx` (additive map entries only, can't change existing tone mappings) and `api/types.ts`/`api/endpoints.ts` (additive interfaces/functions only, no existing export is changed or removed). |

---

## Rollback

If this feature needs to be reverted: revert the five files listed above (`Evaluation.tsx`, `endpoints.ts`, `types.ts`, `Badge.tsx`) — no migrations exist to roll back, no API compatibility concern (the backend endpoint being called already existed and is untouched, so reverting the frontend doesn't orphan any server-side change). A `git revert` of this feature's commit is sufficient; no coordinated backend rollback is needed since none is required in the first place.

---

## Impact Summary

| Area | Change |
|---|---|
| Backend API | Additive response-schema change only — no new endpoints, no route changes, no request-contract changes |
| Database | None |
| Models | None |
| Schemas (backend) | 1 additive change — `ComplianceMatrixEntryRead` gains 3 optional fields (`verified_by`, `verified_by_name`, `verified_at`) |
| Frontend Components | 3 modified (`Evaluation.tsx`'s `MatrixRow` + `BusinessDecisionPanel`, `Badge.tsx`) |
| New Components | 1 (`VerificationForm`, inline within `Evaluation.tsx`, local state only) |
| Existing APIs Reused | 2 (`POST /compliance/{id}/verify`, `GET /evaluation/{missionId}`) |
| New APIs | 0 |
| Migrations | 0 |
| Breaking Changes | None |

---

## Amendments (post-discussion, pre-implementation)

Resolved through review before any code was written:

1. **Row expansion state.** Dropped page-level `verifyingRowId`/`verificationDraft`/`savingVerification`. Moved to local state inside `MatrixRow` (`isVerifying`, `draftStatus`, `draftNote`, `saving`) — matches the existing independent, uncoupled `<details>` pattern already used for the evidence trail. Multiple rows' verification forms can be open simultaneously; nothing coordinates them, because nothing needs to.
2. **Verified-by/when — complete field set, one shot.** `ComplianceMatrixEntryRead` (`backend/app/schemas/decision.py:35-57`) does not currently expose `verified_by` or `verified_at`, only `requires_verification`/`verification_reason`/`verification_status`. The complete set of verification metadata on the `ComplianceMatrix` ORM row is exactly six fields — those three plus `verified_by`, `verified_at`, and (not a separate column — folded into the shared `notes` field by `verify_compliance_row()`) the human's note. Adding all three missing fields now, flat and additive (consistent with every other field on this schema, no nesting introduced), avoids exposing them one at a time across future releases:
   - `verified_by: uuid.UUID | None = None`, `verified_at: datetime | None = None` — already on the ORM row, free via `model_validate()`, no extra query.
   - `verified_by_name: str | None = None` — resolved via one small batch lookup against `User`, structurally identical to the existing `resolve_evidence_sources()` (`backend/app/services/decision_service.py:318-377`), attached the same way `evidence_source` already is (`model_copy(update=...)` in `_build_response()`, `backend/app/api/v1/evaluation.py:34-50`).
   - Badge shows "Verified Compliant · Verified by {name} · {relative time}" once this lands — no "by you," since another user viewing later must see the real verifier.
3. **Blocking calculation reframed.** No backend logic is duplicated. `verification_status !== "pending"` is a reliable client-side proxy for "already verified" (the backend always sets `verification_status` and `verified_by` together, never one without the other — `approval_service.py:95-97`), so the readiness banner is computed entirely from fields already on the wire today (`risk_level`, `requires_verification`, `verification_status`). The backend's `get_blocking_rows()` remains the sole enforcement; the frontend banner is guidance, not a second copy of the rule, and the 409 stays as defense in depth.
4. **Verify button visibility.** Gated on `mission.status === "awaiting_approval"` in addition to `entry.requires_verification` — hidden/disabled otherwise rather than always rendering toward a guaranteed 409 once a mission is finalized. Requires threading mission status into `MatrixRow` as a new prop (it doesn't receive it today) — noted as a small addition to the "Files to be Modified" section above, not a new file.
5. **Performance — confirmed as understood.** One additional `POST` per verify click; no polling; no background sync; no additional evaluation requests; no backend performance impact (`verify_compliance_row()` is a single-row update plus one `AuditLog` insert).

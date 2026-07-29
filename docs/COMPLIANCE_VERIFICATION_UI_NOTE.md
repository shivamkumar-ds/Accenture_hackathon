# Compliance Verification UI — Design Note

Status: **Proposed, not implemented.** Written before any code, per the gap the Architecture Conformance Review surfaced: `record_decision()`'s blocking-row gate (`backend/app/services/approval_service.py:56-66,128-134`) has a working backend, `POST /compliance/{id}/verify` (`backend/app/api/v1/approval.py:36-52`), with no frontend UI at all. This note answers the six questions asked before writing that UI, grounded in what the backend already does — not proposing new backend behavior.

## 1. Where does the Verify button appear?

Inline, on the Compliance Matrix rows in `Evaluation.tsx` (`MatrixRow`, `frontend/src/pages/Evaluation.tsx:345-399`) — the same component that already renders the "View evidence trail" disclosure. Verify is a sibling action, not a separate page: a row already shows everything a human needs to make the call (requirement, status, risk, evidence trail), so sending them elsewhere to act on it would break the exact evidence-first flow `CORE_ARCHITECTURE.md` §1 describes.

Shown only on rows where `requires_verification === true` (an existing field already on `ComplianceMatrixEntryRead`, `frontend/src/api/types.ts:207`). Rows at `risk_level` HIGH/CRITICAL get a visually distinct treatment (they're the ones that actually block Save) — but the button itself isn't restricted to blocking rows, since `requires_verification` can be true at MEDIUM/LOW too (advisory, not gating, per `BLOCKING_RISK_LEVELS`, `approval_service.py:29-32`), and a human should be able to clear those too, just without urgency styling.

## 2. Who can see it?

Everyone viewing the Decision Screen sees the button — no client-side role-gating. This matches the existing convention in this codebase: nothing in the frontend today hides an action based on the current user's role (e.g. capability deletion is `require_administrator`-only server-side, but the delete icon isn't conditionally hidden client-side either). Authorization is enforced server-side by `require_approver` (`backend/app/api/deps.py:73-87` — Executive or Administrator) exactly as it is today; an unauthorized click surfaces the resulting 403 as a toast via the existing `extractErrorMessage` pattern, same as every other write action in this app.

Worth flagging, not fixing now: `require_approver` and `require_business_decision_permission` (the Bid Decision gate) currently resolve to the identical role set (Executive/Administrator) but are two separately-named permissions. If a future customer wants "Bid Manager can verify rows but not record the final decision," that's already possible without touching this UI — only `require_approver`'s predicate changes.

## 3. What happens after clicking Verify?

Clicking "Verify" expands an inline form on that row (same interaction pattern as the existing evidence-trail `<details>` disclosure) with:

- Three choices — Verified Compliant / Verified Non-Compliant / Escalated (`ComplianceMatrixVerificationStatus`, excluding `PENDING`, which the backend schema already rejects as a target value — `VerifyComplianceRequest._reject_pending`, `backend/app/schemas/approval.py`).
- An optional note.
- A confirm button, calling `POST /compliance/{id}/verify`.

On success, the row re-renders in place with a "Verified" badge and the form collapses — no navigation, no page reload, matching Bid Decision's own "no draft state, save or nothing changed" discipline (`BID_DECISION_DESIGN.md` §3 item 5). The badge shows the real verifier and timestamp ("Verified Compliant · Verified by {name} · {relative time}"), never "by you" — the same mission can be viewed later by someone else, so the UI must represent the actual verifier, not the current viewer. See the Implementation Plan's Amendments for the small additive schema change (`verified_by`, `verified_by_name`, `verified_at`) this requires.

## 4. Can a verification be undone?

Yes, implicitly — the backend already supports this without any change. `verify_compliance_row()` has no "already verified" guard; calling it again on the same row overwrites `verification_status`, `verified_by`, and `verified_at` (`approval_service.py:95-97`), as long as the mission is still `AWAITING_APPROVAL` (the same check that blocks verification after a mission is finalized also implicitly blocks changing your mind after the fact — correctly, since a finalized decision's evidence should be historical, per the existing comment at `approval_service.py:86-89`).

UI-side: once verified, the row shows a "Change verification" link instead of hiding the action entirely, re-opening the same inline form. No separate "undo" concept needed — re-verifying with a different status *is* the undo path, and it's consistent with how the backend already models it.

## 5. How is the audit trail shown?

Minimally, for V1 — consistent with Bid Decision's own explicit exclusion of a history timeline (`BID_DECISION_DESIGN.md` §3: "Explicitly not present: ... history timeline"). Each verify call already writes to `AuditLog` via `_log()` (`approval_service.py:104-108`), and `GET /approval/{mission_id}` already exposes it as `decision_events` (`ApprovalHistoryResponse`, defined in `frontend/src/api/types.ts:291-296`, fetched by `getApprovalHistory()` — currently unused anywhere in the UI, per the conformance review).

For this feature, the audit trail surfaces only as the row's current state (status/by/when), not a full log. A dedicated history view is future work using the same already-existing endpoint — no new backend work required when that's justified by real usage, exactly the same "don't build it until it's needed" discipline `BID_DECISION_DESIGN.md` §6 already applies to Bid Decision's own history.

## 6. What happens if there are multiple blocking rows?

Today, a user only finds out via a 409 on Save, with a message listing raw compliance-row UUIDs (`approval_service.py:131-134`) — a dead end, not a guided flow. This UI should close that gap: the `BusinessDecisionPanel` (`frontend/src/pages/Evaluation.tsx:429-524`) already has every field it needs client-side (`risk_level`, `requires_verification`, `verification_status` are all already on `ComplianceMatrixEntryRead`) to compute the same blocking set the backend will check, before the user ever clicks Save.

Proposed behavior: if any row is HIGH/CRITICAL + `requires_verification` + not yet verified, show a banner in the Business Decision panel — "N item(s) must be verified before you can save a decision" — and disable the Save button, the same way it's already disabled when the mission isn't `awaiting_approval`. This turns the backend's hard gate into a guided step instead of a trial-and-error 409, without changing any backend behavior — the 409 stays as defense in depth for the direct-API case, exactly as it already is for every other validated write in this codebase.

## Not in scope for this UI

Same discipline as Bid Decision itself: no bulk-verify action, no notifications when a row needs verification, no reassignment/task-queue concept. One row, one human decision, same as the existing per-Verdict override philosophy in `CORE_ARCHITECTURE.md` §7 — nothing here should turn into a workflow engine.

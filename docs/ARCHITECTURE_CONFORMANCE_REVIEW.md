# Architecture Conformance Review

Read-only audit. Checks the current codebase (`backend/app`, `frontend/src`, as of commit `392ad4b`) against `docs/CORE_ARCHITECTURE.md`, `docs/AI_ARCHITECTURE_PRINCIPLES.md`, and `docs/BID_DECISION_DESIGN.md`. No code was modified to produce this review.

Classification legend: **Implemented** (built and verifiable in code) · **Partially Implemented** (real but incomplete — a documented guarantee holds in one layer but not another) · **Planned** (explicitly marked future work in the docs themselves — not a gap, a deferred decision) · **Not Started** (described as current-state in a doc, but no code exists) · **Architecture Drift** (code and documentation actively disagree — either overclaims or a real divergence in behavior).

---

## Part 1 — `CORE_ARCHITECTURE.md`

### §1 Core Philosophy

| Item | Status | Evidence |
|---|---|---|
| Evidence-first (traceable link to requirement/evidence/reasoning step) | **Implemented** | `ComplianceMatrix.supporting_evidence`, `.notes`, `.evidence_reference` (`backend/app/models/recommendation.py:53-54,71`); resolved to a human-readable trail by `resolve_evidence_sources()` (`backend/app/services/decision_service.py:318-377`); rendered end-to-end in `MatrixRow` (`frontend/src/pages/Evaluation.tsx:356-399`). |
| Confidence never asserted without a computable basis | **Implemented** | Every confidence value traces to an arithmetic function, not an LLM self-report: `compute_confidence_propagation()` (`backend/app/agents/decision_engine.py:227-263`), extraction confidence from OCR word-confidence or a fixed baseline (`backend/app/agents/capability_builder.py:104-119`). |
| Human-in-the-loop at every layer, not just the final call | **Partially Implemented** | See §7 below — the atomic-layer override exists as an API (`verify_compliance_row`, `backend/app/services/approval_service.py:69-109`) but has **no frontend UI** (verified: no reference to `/compliance/` or a verify action anywhere in `frontend/src`). A human can only exercise this override via direct API call today, not through the product. |
| Never hide uncertainty (surface conflict, don't silently pick) | **Not Started** | No code implements multiple-candidate-interpretation surfacing. See §5 below. |

### §2 The Atomic Object (Requirement → Evidence → Evaluation → Verdict)

| Item | Status | Evidence |
|---|---|---|
| Requirement (atomic claim, source page, type, mandatory flag) | **Implemented** | `Requirement` model: `requirement_type`, `description`, `mandatory`, `source_page`, `confidence` (`backend/app/models/tender.py:30-42`). |
| Evidence (from Capability Graph, own freshness/staleness state) | **Implemented** | Five capability entity tables, company-scoped not mission-scoped so they're reusable (`backend/app/models/capability.py:20-102`); freshness computed per-entity at read time (`backend/app/services/freshness.py:19-43`). |
| Evaluation decomposed into deterministic + judgment sub-checks | **Implemented** | `match_requirement()` (`backend/app/agents/decision_engine.py:102-174`) is the clearest evidence in the codebase for this principle: procedural categories skip the LLM entirely (line 105-106, `build_procedural_result`, lines 83-99); a zero-candidate result is a deterministic DB fact, not a guess (lines 108-120); the *one* genuine judgment sub-check is the LLM call at lines 123-129; freshness is then applied as a deterministic override on top of the LLM's output (lines 149-162), including expiry forcing `NOT_MET` regardless of what the LLM said. |
| Verdict (met/not_met/conditional/review_required, risk level, reasoning trace) | **Implemented** | `MatchStatus` enum matches exactly (`backend/app/models/enums.py:69-75`); persisted as `ComplianceMatrix.status`/`.risk_level`/`.notes` (`backend/app/models/recommendation.py:52,59-61,54`); risk computed deterministically by `compute_risk_level()` (`backend/app/agents/decision_engine.py:177-186`). |
| Decision aggregates Verdicts into Go/No-Go | **Implemented** | `compute_recommendation_type()` (`backend/app/agents/decision_engine.py:202-214`) — pure deterministic function over `MatchResult` list, never LLM-generated. |
| Readiness = pure aggregate function over Verdicts | **Not Started** | No "readiness" concept exists anywhere in `backend/app` (confirmed via repo-wide search — zero matches). The closest analog is the frontend's `Compliance Summary` stat row (`frontend/src/pages/Evaluation.tsx:250-259`, `statusCount()` at line 44-46), computed client-side from raw counts, not a named, backend-defined readiness percentage. |
| Risk = attribute of a Verdict, not independent entity | **Implemented** | `ComplianceMatrix.risk_level` (`backend/app/models/recommendation.py:59-61`) — a column on the Verdict row, no separate Risk table. |
| Capability Graph = structured evidence source | **Implemented** | See Evidence row above; `capability_service.list_capabilities()` is the single read path decision matching draws from (`backend/app/services/decision_service.py:120`). |
| Audit trail / explainability = reasoning trace surfaced, not regenerated | **Implemented** | `resolve_evidence_sources()` reads the already-persisted `evidence_reference` rather than recomputing anything (`backend/app/services/decision_service.py:318-377`, explicit in its own docstring: "read-time resolution only, nothing new is persisted"). |
| Outcome tracking references Verdicts | **Not Started** | `Mission.actual_outcome`/`.outcome_notes` columns exist (`backend/app/models/mission.py:51-52`) but are **never written by any service** (confirmed via repo-wide search — only referenced in the model and its Pydantic schema, `backend/app/schemas/mission.py:24-25`). Business Decision (Phase B) deliberately did not use these columns — see Part 3, §5/§6 below. Per-Verdict outcome attribution specifically is listed in §10 as not-yet-designed, consistent with this being Not Started rather than drift. |

### §3 The 8 Architectural Principles

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | AI is a scarce resource | **Implemented** | Every non-judgment step in `decision_engine.py` is a plain Python function (`compute_risk_level`, `compute_requires_verification`, `compute_recommendation_type`, `compute_confidence_propagation`, `build_executive_summary` — lines 177-285); exactly one LLM call type exists in the whole module (module docstring, line 6: "Only one LLM call type exists in this whole module"). |
| 2 | Intelligence should compound | **Implemented** | Capability entities are company-scoped, not mission-scoped (`backend/app/models/capability.py` — no `mission_id`/`tender_id` FK on any of the five tables), so one extraction is reusable across every future tender for that company. |
| 3 | Reason once / reuse while valid / recompute on change | **Not Started** | No reuse-across-evaluations mechanism exists. Every call to `run_evaluation()` recomputes every requirement's match from scratch via a fresh LLM call (`backend/app/services/decision_service.py:159-163`, unconditional `asyncio.gather` over all requirements) — there is no lookup-before-compute step, no Verdict cache, and no version/hash field on `Requirement` or `ComplianceMatrix` to key a cache on. This is the same gap as §6 Caching Strategy below (Not Started) and Phase A's `cache_hit` telemetry column (see Part 4 — column exists, always `False`, nothing ever sets it `True`). |
| 4 | Separate knowledge from reasoning | **Implemented** | `_summarize_entity()` (`backend/app/agents/decision_engine.py:69-80`) hands the LLM pre-extracted structured facts, never raw documents; the LLM's only input is those summaries plus the requirement text (line 126). |
| 5 | Recommendation quality is sacred | **Partially Implemented** | No code actively violates this (no cost-vs-quality tradeoff logic exists at all), but there's also no explicit mechanism *enforcing* it — e.g., no quality-regression test gating a prompt or model change. Absence of violation, not presence of a guarantee. |
| 6 | Product value should compound (moat = accumulated data) | **Implemented** | Same evidence as Principle 2 — Capability Graph, Requirement/Evidence/Verdict history persist and accumulate per company across missions. |
| 7 | Every feature must strengthen the moat | **Planned** | This is a design-time discipline (a question asked before building), not something a static code check can verify. Evidence is procedural: `docs/BID_DECISION_DESIGN.md` explicitly frames its own scope against this test (§1: "if it doesn't fit... it belongs in a later version"). |
| 8 | Every AI conclusion must be traceable | **Implemented** | Same evidence as §1/§2 Evidence-first rows above — every Verdict's `notes` field carries the LLM's `reasoning` output verbatim (`decision_engine.py:143`) plus any deterministic override applied on top (lines 153,157-159,162). |

### §4 Versioning

**Not Started.** `Requirement` has no version, `supersedes_id`, or `superseded` field of any kind (`backend/app/models/tender.py:30-42` — confirmed by full read of the model). A repo-wide search for `supersede`/`corrigend` outside documentation returns only an unrelated comment in `revalidation_service.py` about superseded *Recommendations* (evaluation runs), not Requirement versions. Corrigendum handling described in this section does not exist in any form.

### §5 Multiple Interpretations

**Not Started.** A repo-wide search for `interpretation`/`contradiction` returns zero matches in `backend/app`. `tender_analyzer.py`'s deduplication logic (`_deduplicate()`, `backend/app/agents/tender_analyzer.py:81-98`) does the opposite of what this section describes: it collapses exact-duplicate requirement text down to one row, but has no mechanism to detect or preserve *conflicting* values for the same requirement (e.g., summary vs. annexure disagreement). No "Contradiction Finder" equivalent exists.

### §6 Caching Strategy

**Not Started.** No caching layer exists anywhere in the evaluation pipeline. `run_evaluation()` always performs a fresh LLM call per requirement per run (`backend/app/services/decision_service.py:145-163`), with no lookup against prior Verdicts for structurally similar requirements, no Evidence Version/content-hash field on any model, and no Evaluation Logic Version field anywhere. Phase A's telemetry schema anticipated this (`LLMCallEvent.cache_hit`, `backend/app/models/telemetry.py:54`), but the column is never set to `True` by any caller — `record_llm_call()` doesn't even accept a `cache_hit` parameter (`backend/app/core/telemetry.py:31-43`). This is the single largest gap between the frozen architecture and the current build.

### §7 Human-in-the-Loop

| Item | Status | Evidence |
|---|---|---|
| Atomic-layer override (verify/reject individual Verdict) | **Partially Implemented / Architecture Drift** | The API exists and is fully functional: `verify_compliance_row()` (`backend/app/services/approval_service.py:69-109`), exposed as `POST /compliance/{id}/verify` (`backend/app/api/v1/approval.py:36-52`). But the document's own claim — "this already exists in the product today" (`CORE_ARCHITECTURE.md:67`) — **overstates what's true**: there is no frontend UI for it at all (confirmed: zero references to `/compliance/` or a verify action in `frontend/src`). This is drift in the documentation's framing, not in the backend code, but it's operationally significant: `record_decision()`'s blocking-row gate (see §4 of the Bid Decision review below) depends on a human being able to verify a row, and there is currently no way to do that except a raw API call. |
| Aggregate-layer Business Decision (Proceed/Rejected/Needs Changes) | **Implemented** | `record_decision()` (`backend/app/services/approval_service.py:112-145`), UI in `BusinessDecisionPanel` (`frontend/src/pages/Evaluation.tsx:429-524`). Full detail in Part 3. |
| AI never issues a submit/don't-submit recommendation | **Implemented** | `RecommendationType` is always computed by the deterministic `compute_recommendation_type()` (`backend/app/agents/decision_engine.py:202-214`) — never asked of the LLM directly. The LLM's only output feeding into this is a per-requirement `status` (met/not_met/etc.), not a go/no-go verdict. |

### §8 AI Boundaries

| Item | Status | Evidence |
|---|---|---|
| LLM used only for genuine judgment sub-check | **Implemented** | See §2/§3 evidence above. |
| LLM used for summarizing computed results into an executive summary | **Architecture Drift** | The document states the LLM is used for this (`CORE_ARCHITECTURE.md:71`). It is not: `build_executive_summary()` is an explicit deterministic string template, and its own docstring says so — *"Deterministic string template, not an LLM call — see the strategy note on why"* (`backend/app/agents/decision_engine.py:266-269`). The implementation is **more conservative** than the architecture document describes, not less — a favorable drift, but a factual mismatch that should be corrected in the doc rather than left implying an LLM call that doesn't happen. |
| Never guesses deterministic facts (dates, amounts, registration numbers) | **Implemented** | No code path substitutes an LLM guess for a regex/structured-field extraction where one is available; the one arguable gray area (structured extraction of employee/certification/project fields from raw PDF text) is a legitimate extraction task, not "guessing an already-known fact." |
| Never invents unsupported categories | **Implemented** | No commercial/legal/competitive/strategic-advice code path exists anywhere; `RequirementType` and `CapabilityEntityType` enums are closed sets (`backend/app/models/enums.py`). |
| Never issues a submission verdict | **Implemented** | Same evidence as §7 above. |
| Confidence/readiness maps to one named, computable statistic | **Implemented** | Every confidence field traces to a named function (`compute_confidence_propagation`, `_compute_confidence` in `capability_builder.py:104-119`) — no blended or invented number. |
| **Documentation gap (not a code violation):** §8's own boundary list only names two sanctioned LLM uses (judgment sub-check, summarization) but the codebase has a third, real, load-bearing use — structured extraction from unstructured documents (`capability_builder.py`, `tender_analyzer.py`). This is consistent with §3 Principle 4's spirit ("facts come from structured extraction... deterministic rules") but §8's literal wording doesn't acknowledge extraction as a sanctioned category, creating a textual ambiguity a future reviewer could misread as a violation. Recommend adding it explicitly to §8. |

### §9 Non-Core Components

| Item | Status | Evidence |
|---|---|---|
| Tender metadata pre-fill | **Implemented** | `extract_tender_metadata()` (`backend/app/services/tender_service.py:65`), `POST /tenders/extract-metadata` (`backend/app/api/v1/tenders.py:72-80`) — correctly optional (best-effort, never persisted, per its own docstring). |
| Model tier routing (cheap vs. premium) | **Not Started** | No tier/model-switching logic exists in `backend/app/core/config.py` — one fixed model per provider, selected only by `LLM_PROVIDER`, not by task cost/quality tradeoff. Correctly non-core per the doc's own framing, so this is not a gap, just confirmed absent. |
| External enrichment (Udyam, circulars, portal metadata) | **Not Started** | No code touches any external government data source. Consistent with §10 below, which lists this as unresolved and pending verification — no drift. |

### §10 Future Extensions

All items in this section are explicitly framed as "Not Yet Designed, Not Yet Approved" — so **Planned** is the correct classification for the section as a whole, not a gap. Verified each individually to confirm none have accidentally been built (which would itself be a process violation, building ahead of design approval):

- Decision rationale capture (structured fields) — **Not Started**, confirmed: `reason` on `ApprovalDecisionRequest` is a single freeform string (`backend/app/schemas/approval.py`), no `business_reason`/`assumptions` fields exist.
- Per-Verdict outcome attribution — **Not Started**, confirmed (see §2 Outcome tracking row above).
- Udyam registration verification — **Not Started**, confirmed, no code references it.
- Requirement composite structure — **Not Started**, confirmed: `Requirement` is flat (see §4 above).
- Claim pre-classification step — **Not Started**, confirmed: `tender_analyzer.py` extracts directly into `Requirement`-shaped objects with no intermediate `Claim` stage.
- Evaluation as its own sub-engine — **Not Started** as a formal structure, though the *spirit* of it already exists informally inside `match_requirement()` (deterministic checks, then one semantic check, then a deterministic freshness override — three de facto stages in one function). Correctly not over-built into a separate module per the doc's own caution against building for hypothetical scale.
- Business-decision factors excluded from the R-E-V engine, never AI-scored — **Implemented** (as an absence of violation): `reason` in the Business Decision flow is stored verbatim, never parsed, scored, or fed to any model (`backend/app/services/approval_service.py:136` — passed straight to `_log()` as a string).
- GeM/CPPP data access — **Not Started**/unresolved, confirmed, no code references it.

---

## Part 2 — `AI_ARCHITECTURE_PRINCIPLES.md`

This document is a condensed restatement of `CORE_ARCHITECTURE.md` §3 plus five standing guardrails. The 8 principles were already verified individually in Part 1 §3 with citations; they are not re-cited here to avoid duplication. Findings below cover only the guardrails, which are distinct testable claims not covered above.

| Guardrail | Status | Evidence |
|---|---|---|
| Never issue an AI-generated submit/don't-submit verdict | **Implemented** | See Part 1 §7/§8. |
| Never invent a category the pipeline has no data to support | **Implemented** | See Part 1 §8. |
| Never present a confidence/readiness number that isn't one named, computable statistic | **Implemented** | See Part 1 §8. Note: "readiness" specifically doesn't exist as a concept at all yet (Part 1 §2), so this guardrail is vacuously satisfied for readiness — there's no readiness number to misrepresent, computable or otherwise. |
| External data sources are enhancements, never dependencies | **Implemented** | No external source is called anywhere in the core evaluation path (`decision_engine.py`, `decision_service.py`); the one external-adjacent feature (tender metadata pre-fill) is explicitly best-effort and non-blocking (Part 1 §9). |
| No feature ships on assumption where verification is possible and hasn't been done | **Partially Implemented** | Followed as an explicit practice during this conversation (e.g., the GeM/CPPP access question was left unresolved rather than assumed; the Bid Decision implementation path was verified against actual code before building — see Part 3 header note). Not something a static code scan alone can fully confirm, since it's a process discipline, not a code property. |

---

## Part 3 — `BID_DECISION_DESIGN.md`

Note: this document's own status line (line 3) already discloses that §4/§5/§6/§7 were revised mid-implementation after discovering `approval_service.record_decision` predated the design conversation. That self-correction is itself good evidence the doc is being kept honest rather than aspirational — verified below section by section.

| § | Item | Status | Evidence |
|---|---|---|---|
| 1 | Product contract (read existing data, write one decision, no new computation) | **Implemented** | `record_decision()` performs no evaluation computation, only reads `mission.recommendation_id`/`get_blocking_rows()` and writes status/`AuditLog` (`backend/app/services/approval_service.py:112-145`). |
| 2 | Entry point: "Make Business Decision" button on Reports, next to "Download PDF Report" | **Implemented** | `frontend/src/pages/Reports.tsx:189-192` (button added, `Gavel` icon, links to `/missions/{id}`). |
| 3 | Page layout: AI Analysis / Business Decision divide | **Implemented** | `frontend/src/pages/Evaluation.tsx:355-360` (divider comment + conditional render), `BusinessDecisionPanel` component at lines 429-524. |
| 3 | Decision Summary stats box (critical/high-risk counts, requirements reviewed vs. met, as one distinct box) | **Partially Implemented** | The *information* exists — `Risk Summary` card and `Compliance Summary` stat row (`frontend/src/pages/Evaluation.tsx:224-259`) — but not as the single unified "Decision Summary" box the design doc describes with critical-count and high-count broken out separately. Functionally equivalent, not a literal implementation of §3 item 1. |
| 3 | "Why" section grouped by `requirement_type`, collapsible, defaults open only for not_met/review_required | **Implemented** | `STATUS_ORDER`/grouping logic (`frontend/src/pages/Evaluation.tsx:35,120-124`), `expanded` state defaults (lines 60-65: `not_met: true, review_required: true, conditional: false, met: false`). Note: grouped by `status`, not literally by `requirement_type` as §3 item 3 states — a minor terminology mismatch between the design doc and what was actually built (grouping by outcome status, not by requirement category), though it serves the same "surface what needs attention first" goal. |
| 3 | Business Decision: three-way Proceed/Rejected/Needs Changes selector + notes + Save | **Implemented** | `DECISION_OPTIONS` (`frontend/src/pages/Evaluation.tsx:419-427`), `Textarea` for notes (line ~500), `Save Decision` button calling `recordDecision()` (lines 461-475). |
| 3 | "Needs Changes" UI label over `needs_revision` value (display-only relabel) | **Implemented** | `frontend/src/pages/Evaluation.tsx:426` — label `"Needs Changes"`, value stays `"needs_revision"`. |
| 3 | Explicitly not present: confidence selector, approver field, history timeline, task list | **Implemented** (as correct absence) | Confirmed: no confidence input exists in `BusinessDecisionPanel`; approver comes from `get_current_user`/JWT only (`backend/app/api/v1/approval.py:58`), never a form field; `getApprovalHistory()` is defined (`frontend/src/api/endpoints.ts:154-155`) but never called from any page — the data exists server-side, no history UI was built, matching the doc's intent. |
| 4 | No new endpoint, no new tables — reuses `POST/GET /api/v1/approval` | **Implemented** | Confirmed via `alembic heads` (single head, no new migration added in Phase B) and `backend/app/api/v1/approval.py:55-70`. |
| 4 | `BusinessDecision` kept separate from `RecommendationType` | **Implemented** | `backend/app/models/enums.py:95-108` (separate enum, distinct docstring explaining why). |
| 4 | `reason` required only when `decision == rejected` | **Implemented** | `ApprovalDecisionRequest._require_reason_for_rejected()` (`backend/app/schemas/approval.py`) — validated by `tests/test_bid_decision.py::TestApprovalDecisionRequestValidation`. |
| 4 | Blocking-row gate (409 on unverified HIGH/CRITICAL row) | **Implemented** | `get_blocking_rows()`/gate check (`backend/app/services/approval_service.py:56-66,128-134`) — but see the §7/Part 1 finding above: **this gate is currently very hard to clear in practice**, since there is no frontend UI to verify a compliance row at all. A mission with any unverified HIGH/CRITICAL row is effectively stuck until someone calls `POST /compliance/{id}/verify` directly via API. This is the single most consequential cross-document finding in this review — flagged here and in Part 1 §7, not fixed (read-only audit). |
| 5 | State transition table (proceed/rejected → completed; needs_revision → unchanged) | **Implemented** | `TERMINAL_DECISIONS`/status assignment (`backend/app/services/approval_service.py:27,138-141`), verified by `tests/test_bid_decision.py::TestBusinessDecisionTransitions` (3/3 passing). |
| 5 | Every decision (terminal or not) written to `AuditLog` | **Implemented** | `_log()` call unconditional at line 136, before the terminal/non-terminal branch. |
| 5 | Visibility: completed missions move out of active views but stay queryable | **Not Verified / Likely Not Started** | No filter logic referencing `MissionStatus.COMPLETED` was found in `frontend/src/pages/Reports.tsx` or `Missions.tsx` beyond what already existed for `archived`. This specific "Completed filter" behavior described in §5 does not appear to have distinct handling from before Phase B — worth confirming directly with the Tender Workspace/Dashboard filter logic in a follow-up pass, flagged here as unverified rather than asserted either way. |
| 6 | Audit log now correctly *not* out of scope (revised) | **Implemented** | Matches Part 1 §7 evidence — `AuditLog` reused, no new table. |
| 6 | Structured business-reasoning fields — still out of scope | **Not Started** (correctly, per doc) | Confirmed, see Part 1 §10. |
| 6 | No new migration | **Implemented** | Confirmed via `alembic heads` — single head, unchanged table set. |
| 7 | Permission-shaped authorization, not hardcoded role check inline | **Implemented** | `user_can_make_business_decision()`/`require_business_decision_permission()` (`backend/app/api/deps.py:101-113`), wired onto the route at `backend/app/api/v1/approval.py:58`. Verified by `tests/test_bid_decision.py::TestBusinessDecisionPermission` (covers all 5 roles). |
| 8 | Reopen Decision flow | **Not Started** (correctly, per doc — explicitly "not committing to building it") | Confirmed, no code exists. |
| 8 | Evaluation Version linkage for staleness flagging | **Not Started** (correctly, per doc) | Confirmed — no version field links a `Mission`'s decision back to the `Recommendation`/evaluation it was made against beyond the existing `Mission.recommendation_id` FK, which is overwritten on every re-run (`decision_service.py:244-247`), so a completed decision has no way to detect the evaluation underneath it has since changed. This is the exact gap the doc's §8 note already names as future work — no drift, just confirming the gap is real and not yet mitigated. |

---

## Summary of Findings Requiring Attention

Ranked by operational consequence, not by document order:

1. **Compliance-row verification has no UI** (Part 1 §7, Part 3 §4). This is the most consequential finding: the Bid Decision feature's blocking-row gate is a hard 409 with no in-product way to clear it. Any mission with an unverified HIGH/CRITICAL compliance row cannot get a recorded decision at all right now, through the UI, for any user.
2. **No caching layer exists** (Part 1 §3 Principle 3, §6). The architecture's caching strategy is fully specified but entirely unbuilt; every evaluation run recomputes every requirement from scratch, and Phase A's `cache_hit` telemetry column is a placeholder no code path ever sets.
3. **`CORE_ARCHITECTURE.md` §7 overclaims** that atomic-layer override "already exists in the product today" — it exists in the API, not the product a user can reach.
4. **`CORE_ARCHITECTURE.md` §8 misdescribes the executive summary as LLM-generated** — it's deterministic. The implementation is more disciplined than the doc claims, but the doc should be corrected for accuracy.
5. **Two dead Mission columns** (`actual_outcome`, `outcome_notes`) exist in the schema and Pydantic model but are never written by any service — a residue from before the Human Approval Layer / `AuditLog` mechanism was connected to Bid Decision.
6. Requirement versioning (§4), multiple interpretations (§5), and readiness-as-a-named-concept (§2) are all genuinely Not Started — consistent with their framing elsewhere as later-phase work, not silently dropped commitments.

No modifications were made to any file to produce this review, per the read-only instruction.

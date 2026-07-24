# BidOps AI — Engineering Decisions Log

**Numbering note (Milestone 6 housekeeping):** IDs D-101 through D-144 were made sequential and
unique in this pass (D-145 onward are new decisions added after the renumbering, not part of
it). Earlier drafts of this log reused D-112 through D-116 twice each
(once pre-M10, once in the M11/M11.5/consolidation era) and had no D-107. Both were fixed in a
documentation-only renumbering — no decision's content, reasoning, or outcome changed, only
its ID. If you have an old citation to one of these IDs from before this pass, the mapping is:
former D-108→D-107, D-109→D-108, D-110→D-109, D-111→D-110, first D-112→D-111, first
D-113→D-112, first D-114→D-113, first D-115→D-114, first D-116→D-115, D-117→D-116 (and every
ID from there through the old D-139 shifted down by one to close the gap), second D-112→D-139,
second D-113→D-140, second D-114→D-141, second D-115→D-142, second D-116→D-143. See D-144 for
the milestone that prompted this cleanup.

---

## D-101 — Tender chosen as hackathon build; long-term wedge left open
**What:** Built the MVP around tender/bid decision intelligence rather than vendor-qualification/compliance management.
**Why:** Tender demos better, fits the hackathon track directly, and testing vendor-qualification would require building a second product with zero design partners in that space.
**Alternatives considered:** Vendor/certification-qualification management as the founding wedge.
**Why rejected (for now, not permanently):** No way to observe real usage of a product that doesn't exist — decided to build tender, and treat the wedge question as open, resolved later by real customer evidence.

## D-102 — Capability Graph over generic document memory / RAG
**What:** Company capability represented as a structured, typed, freshness-aware graph rather than a vector store over raw documents.
**Why:** RAG-style retrieval doesn't track expiry, staleness, or provenance.
**Alternatives considered:** Standard RAG over uploaded company documents.
**Why rejected:** Would not support freshness-awareness, evidence citation, or auditability.

## D-103 — Multi-agent architecture (3 core agents + orchestrator), not one large LLM
**What:** Capability Builder, Tender Analysis, Decision Intelligence as separate agents, coordinated by a Mission Orchestrator.
**Why:** Different tool access, different trust boundaries, independent testability.
**Alternatives considered:** Single monolithic prompt; a larger 7-agent ecosystem (including Discovery, Costing, Submission).
**Why rejected:** Monolithic prompt fails on permissioning/auditability; larger ecosystem cut to three for MVP feasibility.

## D-104 — "Autopilot" kept as the product name
**What:** Considered replacing "Autopilot" with "Event-driven Enterprise Decision Intelligence."
**Why kept:** The aviation-autopilot analogy holds structurally — bounded, event-driven autonomy with defined human handoff points.
**Resolution:** "Autopilot" stays as the name; "event-driven decision intelligence" is the precise technical explainer when asked how it works.

## D-105 — Compliance Saves as the single North Star KPI
**What:** Defined as a compliance-matrix row initially Not Met or Review Required, later resolved before the mission deadline.
**Why:** Frequent, leading, and auditable in dollar terms — unlike time-saved (commoditizable) or win rate (causally diffuse).
**Alternatives considered:** Time-saved, win-rate improvement, fabricated win-probability scores.
**Why rejected:** Time-saved doesn't differentiate from a summarizer; win rate is too noisy; win-probability would be fabricated precision.

## D-106 — Capability Snapshot, confidence propagation, and high-risk verification added to schema
**What:** Added immutable per-mission Capability Snapshots, a multi-stage confidence model, and mandatory verification fields on Compliance Matrix rows.
**Why:** Closed a gap between what the architecture promised (reproducibility, human verification) and what the original schema could enforce or audit.
**Alternatives considered:** Single flat confidence score; aggregate mission-level approval alone.
**Why rejected:** A single number can't be explained or audited; aggregate approval risks rubber-stamping without re-verifying the row that matters.

## D-107 — Python 3.12 adopted instead of 3.11
**What:** Development environment already provides Python 3.12.3.
**Why:** Avoided unnecessary environment complexity while maintaining reproducibility — installing a separate 3.11 to match a number picked before seeing the environment would have added complexity for no benefit.
**Date:** M0, Step 1.

## B-001 — Alembic autogenerate does not emit deferred ALTER TABLE for use_alter=True
**What:** Foreign keys marked `use_alter=True` (to break circular references) are correctly excluded from the inline `CREATE TABLE` by the DDL compiler, but Alembic's autogenerate does not automatically add the corresponding `ALTER TABLE ADD CONSTRAINT` afterward.
**Resolution:** Manually add `op.create_foreign_key()` calls after all referenced tables exist in the migration, and always verify circular/deferred constraints against the actual database schema (`\d table_name`), not just against "migration ran without error."
**Category:** Tooling lesson, not a BidOps architecture or application bug.
## B-002 — HTTPBearer returns 403 for a missing Authorization header, not 401
**What:** FastAPI's HTTPBearer(auto_error=True) raises its own 403 "Not authenticated" when no Authorization header is present at all — only a present-but-invalid token reached this app's own 401 logic.
**Resolution:** Set auto_error=False and handle the missing-credentials case explicitly in get_current_user(), so both missing and invalid tokens return 401 uniformly (401 = "authenticate"; 403 = "authenticated, but not permitted" — reserved for require_administrator()).
**Category:** Framework default behavior, caught via explicit end-to-end testing of the "no token" case, not assumed correct.

## D-108 — Kept plain model responses over the documented {success, data} envelope
**What:** 06_API_Design.md documents a global {"success": true/false, "data"/"error": {...}} response envelope. Implementation (M0 and M1) returns plain Pydantic model JSON and FastAPI's native {"detail": ...} error shape instead.
**Why:** HTTP status codes already convey success/failure; an additional envelope layer is redundant nesting for every client to unwrap. Simplicity (Rule 4) favors the plain response when both conventions solve the same problem.
**Scope Boundary note:** Response envelope format is an implementation convention, not one of the four categories requiring founder/ChatGPT/Claude consensus (agent boundaries, DB entities, approval gating, MVP scope) — decided directly, flagged here for visibility rather than silently applied.
**Reversible:** Cheap to add later (e.g., a response middleware) if a concrete reason arises (a frontend client library expecting that exact shape).
## D-109 — Added Document.uploaded_by (M2)
**What:** 05_Database_Design.md's Document table had no field linking an upload to the user who performed it, but M2's DoD requires documents linked to both Company and User.
**Resolution:** Added `uploaded_by` (UUID, NOT NULL, FK -> users.id). Confirmed via autogenerate diff that no other schema drift existed; documents table was empty at migration time, so no backfill was needed.
**Approved:** Explicitly confirmed before implementing, per the Constitution's Scope Boundary (database entity changes require consensus).

## Known, accepted limitation — file type validation
File type checking (M2) validates file extension + client-declared Content-Type only, not actual file content (magic-byte sniffing). A file with a spoofed extension and Content-Type header could bypass this check. Deferred rather than fixed now — adding real content-type detection (e.g. python-magic) is a new dependency and a real scope decision, not a bugfix, and wasn't part of M2's DoD.
## D-110 — LLMClient abstraction: Qwen unreachable from this sandbox, mock used for verification (M3)
**What:** Network egress to Qwen Cloud/DashScope is blocked at the sandbox level (confirmed empirically: x-deny-reason: host_not_allowed, not a missing-credentials issue). No real Qwen extraction has been executed or verified in this sandbox.
**Resolution:** LLMClient Protocol with two implementations — QwenClient (real, built correctly against DashScope's OpenAI-compatible API, unverified by execution here) and MockLLMClient (pattern-matches real parsed document text, used only when LLM_PROVIDER=mock). .env.example documents LLM_PROVIDER=qwen as the intended real setting.
**Action required on your machine:** set LLM_PROVIDER=qwen and a real QWEN_API_KEY in your local .env, then re-run the same capability-build tests documented in this delivery to get first real verification of the actual Qwen call.

## B-003 — OCR text reconstruction discarded line breaks (M3)
**What:** _extract_image and the PDF OCR fallback built text by joining pytesseract.image_to_data's word list with spaces, discarding all line structure. Field-matching (which bounds a value to its own line) then matched across what should have been separate lines, producing corrupted extracted values.
**Resolution:** Use pytesseract.image_to_string() for the actual text (preserves line breaks); image_to_data() is now used only for its per-word confidence scores, not for reconstructing text.
**Caught via:** real OCR testing against a rendered image, not a unit test mock.

## D-111 — Confidence scoring derived from concrete signals, not LLM self-report (M3)
**What:** confidence_score needed a source. Asking the LLM to rate its own confidence 0-1 was considered and rejected.
**Resolution:** OCR word-level confidence (real, from Tesseract) when OCR was used; a fixed 0.95 baseline for native text extraction; both scaled by extraction completeness (fraction of expected fields actually populated).
**Why:** Consistent with every prior review's position that self-reported LLM confidence is unreliable and shouldn't be trusted as a business signal.

## Guard added during self-review — empty extractions
Project has no single named-required field (every column nullable), so a content-free document could otherwise produce a fully empty, meaningless row. Added a check requiring at least one populated field across any entity type, not just the named-required ones for Certification/Employee.
## D-112 — Freshness computed at read time only, never persisted (M4)
**What:** verification_status (stored) vs. a live freshness view were two different options for M4's "identify expired/stale records" requirement.
**Resolution:** is_expired/is_stale/freshness_status are computed fresh on every GET request and returned alongside the stored verification_status, which is never mutated by this milestone.
**Why:** Certificate-expiry-triggered revalidation is explicitly M9's job (event-driven, with cascading re-evaluation of active missions). Mutating verification_status here would do part of M9's work now, out of order, without the cascade logic that's supposed to accompany it.
**Staleness threshold:** 180 days, configurable via CAPABILITY_STALENESS_DAYS — no document specifies a number; verified directly by backdating a real record 200 days and confirming it flips to "stale".
## D-113 — Mission created as an inert side effect of tender upload (M5)
**What:** Tender.mission_id is NOT NULL, but Mission Orchestrator (M7) doesn't exist yet.
**Resolution:** upload_tender() creates a minimal Mission row (mission_type="tender_evaluation", status=CREATED) alongside the Tender, with zero orchestration logic — matches 06_API_Design.md's existing contract (tender upload already returns both Tender ID and Mission ID).
**Not a schema change, not new orchestration:** just implementing what the frozen API doc already specified.

## D-114 — Whole-tender analysis fails if any single chunk fails (M5)
**What:** If one chunk (out of potentially dozens for a 300+ page tender) returns malformed JSON or fails schema validation, the entire analyze_tender() call raises — no partial results are persisted, even though other chunks succeeded.
**Why kept this way:** Consistent with M3's fail-fast philosophy for a single document. Silently discarding a failed chunk and persisting only the successful ones would hide a real extraction problem behind a technically-successful response.
**Real cost, stated plainly:** one bad chunk (out of many) costs the whole analysis on a large tender, not just that chunk's requirements. If this proves too costly in practice (e.g., a single rare LLM JSON glitch repeatedly failing large-tender analyses), the fix is per-chunk error isolation with partial results plus a warning — a real design change, not a bugfix, and not undertaken here without evidence it's actually needed.

## D-115 — Deterministic exact-match deduplication only (M5)
**What:** Duplicate requirements are removed only on exact (requirement_type, normalized description) match — verified against a real deliberate duplicate spanning two pages of a test tender.
**Not built:** fuzzy/semantic duplicate detection (e.g. two differently-worded restatements of the same requirement). Explicitly out of scope per your instruction ("at least deterministic duplicate removal where practical") — semantic dedup would need embedding similarity, a materially different and riskier mechanism (false-positive merges of genuinely distinct requirements).
## B-004 — Mock's conditional-match branch never actually cited an entity (M6)
**What:** `candidate_lines and 0 or None` — the classic Python and/or idiom breaks when the "true" value is 0. Since 0 is falsy, `0 or None` always evaluated to None, so every "conditional" mock result silently failed to cite any entity index, even when candidates existed. Confirmed via a real test: the eligibility row showed evidence_reference: null when a certification should have been cited.
**Resolution:** Replaced with an explicit conditional expression (`0 if candidate_lines else None`). Re-ran the same evaluation and confirmed the conditional row now correctly cites an entity and gets a CapabilityMapping row.
**Category:** Real bug, caught by testing actual output, not by code review alone.

## D-116 — Procedural requirement categories never enter capability matching (M6)
**What:** Deadline, Evaluation Criteria, and Submission Requirements are facts about the tender process, not claims about company capability — there's no entity that could "satisfy" a deadline.
**Resolution:** These three categories skip matching entirely and get an automatic REVIEW_REQUIRED row with a plain note explaining why, rather than being forced through meaningless capability comparison.

## D-117 — Freshness override: expired forces NOT_MET, stale only downgrades MET to REVIEW_REQUIRED (M6)
**What:** How a deterministic freshness check should affect an LLM's match verdict.
**Resolution (per explicit refinement):** Expired cited evidence forces NOT_MET regardless of the original verdict. Stale cited evidence only downgrades a MET verdict to REVIEW_REQUIRED — never to NOT_MET — and a CONDITIONAL verdict stays CONDITIONAL (already appropriately uncertain). The system never rejects a company solely because evidence is stale.
**Verified:** against three real certifications (fresh/expired/backdated-stale) in a single evaluation run — confirmed both override paths fire correctly and independently.

## D-118 — Weighted, capped confidence propagation, not a simple average (M6)
**What:** How to combine document/entity/matching/recommendation confidence into one overall number without letting a weak stage hide behind strong ones.
**Resolution (per explicit refinement):** Weighted average (document 0.15, entity 0.15, matching 0.50 — highest, since it's the engine's core reasoning — recommendation 0.20), then capped so overall can never exceed the lowest individual stage by more than 0.15.
**Verified by hand:** in the test run, the uncapped weighted average was 0.8933; the cap correctly pulled the actual result to 0.8722 because recommendation_confidence (0.7222) was the weak stage — confirming the cap does real work, not just present in code unused.

## D-119 — Mission → AWAITING_APPROVAL is a fact reflected, not orchestration (M6)
**What:** Whether M6 setting Mission.status encroaches on M7's ownership.
**Resolution:** Once a Recommendation exists, a mission is definitionally awaiting approval — this is a fact being reflected, not a sequencing/coordination decision. No retries, no agent coordination, no state-machine logic beyond this single reflection were added.

## D-120 — Re-evaluation creates a new Recommendation, never replaces (M6)
**What:** What happens if /evaluation/run is called again on the same mission.
**Resolution:** Each run is fully independent — new CapabilitySnapshot and Recommendation rows every time; Mission.recommendation_id updated to the latest; older rows never deleted (matches the Database Design Principle that historical decision data is immutable). Verified: re-ran evaluation on the same mission twice: both original and new Recommendation rows persist in Postgres.
**Not built:** real event-triggered re-evaluation with cascading updates to other affected missions — explicitly M9's job.

## D-121 — Both /evaluation/{mission_id} and /recommendations/{mission_id} implemented identically (M6)
**What:** 06_API_Design.md describes these as two separate endpoints with near-identical response content, with no principled distinction found in the doc.
**Resolution:** Both implemented, backed by the same underlying assembly function (get_evaluation_bundle) — not dropping either since both are in the frozen, approved spec, and inventing an artificial difference would be worse than acknowledging they're the same view under two names.

## D-122 — Executive Summary is a deterministic string template, not an LLM call (M6)
**What:** Whether the executive summary should be LLM-generated prose or computed text.
**Resolution:** Deterministic template over already-decided facts (recommendation type, counts by status, overall confidence) — directly serves this milestone's own instruction to avoid black-box behaviour. The only LLM call anywhere in M6 is the per-requirement matching step.
## D-123 — Orchestrated mission scope is Tender Analysis → Decision Intelligence only (M7)
**What:** 07_AI_Agent_Architecture.md's own workflow walkthrough lists Capability Preparation as a mission step, but nothing in the schema connects a Capability Builder action to a specific Mission, and M3 was built (approved) as a standalone, company-level process independent of any tender context.
**Resolution:** Orchestration covers Tender Analysis → Decision Intelligence only. Capability Builder remains standalone — exactly how M3 and M6 (via CapabilitySnapshot, evaluated against whatever capability graph already exists) already actually work together.

## D-124 — New endpoint: POST /missions/{id}/execute
**What:** 06_API_Design.md's Mission section has no execution trigger.
**Resolution:** New endpoint, same precedent as /auth/register (M1) — filling a genuine gap in the frozen spec, not inventing new scope.

## D-125 — No FAILED value added to MissionStatus; failure reverts to CREATED (M7)
**What:** Unlike Document/Tender.processing_status, the frozen MissionStatus enum has no "failed" state, and adding one would be an unauthorized schema change.
**Resolution:** On any stage failure, Mission.status reverts to CREATED — "not yet successfully completed, safe to retry" — with the actual failure detail captured in AuditLog (finally giving this dormant-since-M0 table real purpose) and in Tender.processing_status ("failed") at the step level.
**Verified:** two distinct failure scenarios (blank tender; zero-requirement tender) both correctly reverted Mission to CREATED and allowed a clean retry afterward.

## D-126 — Stage-needed decisions use authoritative status, never row existence (M7, per explicit refinement)
**What:** Whether to (re-)run Tender Analysis is decided by Tender.processing_status != "completed", not by checking whether Requirement rows exist. Whether to (re-)run Decision Intelligence is decided by Mission.status captured *before* this call sets it to RUNNING (since reaching AWAITING_APPROVAL is itself evidence a Recommendation exists), combined with whether analysis just re-ran this call.
**Why:** Keeps orchestration resilient to future event-driven re-analysis (M9) — a status flip back to PENDING correctly triggers re-execution regardless of what rows already exist from a prior run.
**Scope note:** Document.processing_status is not a meaningful gate for this specific two-stage flow — it belongs to M3's capability-document pipeline, which sits outside what M7 orchestrates per D-123.
**Verified:** re-executing an already-completed mission correctly skipped both stages (confirmed no duplicate Recommendation created); re-executing after a partial failure (analysis succeeded, evaluation failed) correctly skipped analysis and retried only evaluation.

## D-127 — Duplicate-execution guard is in-process, not distributed locking (M7)
**What:** Mission.status == RUNNING is checked and rejected (409) before starting.
**Scope:** A real, meaningful check for this single-process MVP — not distributed locking, consistent with the Execution Plan's deferred-scaling-infrastructure stance. Verified by manually setting a mission to RUNNING and confirming execution is correctly rejected.

## D-128 — DELETE /missions/{id} archives, never deletes (M7)
**What:** Matches the Database Design's existing Active/Archived/Deleted soft-delete principle, not a new pattern. Verified: archived missions correctly reject further execution attempts (409, terminal state).
## D-129 — Human decision lives in AuditLog only; no new column, Recommendation stays immutable (M8)
**What:** Where to record a human's final approve/reject/review decision.
**Resolution:** AuditLog only — no new column anywhere, Recommendation is never modified. Verified directly: a human override (CONDITIONAL_GO) that differed from the AI's own recommendation (NO_GO) left the Recommendation row completely untouched in Postgres; the actual decision is only reconstructable from AuditLog.

## D-130 — decision accepts all four RecommendationType values; GO/CONDITIONAL_GO/NO_GO terminate, REVIEW does not (M8)
**What:** Reconciling 06_API_Design.md's four-value decision field with M8's own binary approve/reject framing.
**Resolution:** All four values accepted (preserving the human's authority to record any final call, including full override of the AI). GO, CONDITIONAL_GO, and NO_GO all move Mission to COMPLETED; REVIEW deliberately leaves it at AWAITING_APPROVAL. Verified: a REVIEW decision left the mission open for a second, real decision afterward.

## D-131 — Approval authority: Executive OR Administrator (per explicit refinement)
**What:** Who may record a mission decision.
**Resolution:** Both roles accepted — Executive is the intended production approver; Administrator is allowed so a newly registered company can complete the full workflow without first creating a separate Executive user. Verified: a Bid Manager (neither role) is correctly rejected (403) but can still read approval history.

## D-132 — Only HIGH/CRITICAL + requires_verification blocks a decision; MEDIUM/LOW stay advisory (per explicit refinement)
**What:** Whether every flagged compliance row must be verified before a decision, or only the highest-risk ones.
**Resolution:** Blocking gate checks requires_verification=true AND risk_level in (HIGH, CRITICAL) AND verified_by IS NULL. Verified twice: a mission with unverified CRITICAL+HIGH rows was correctly blocked (409, naming both rows) until verified; a separate mission with only a MEDIUM-risk unverified row approved successfully without it.

## D-133 — Compliance verification locked after mission finalization (interpretive addition, not explicitly requested)
**What:** Whether a compliance row can be edited/verified after its mission has already reached a terminal decision.
**Resolution:** Locked — matches "nothing overwrites historical recommendations" applied to the evidence backing them, not just the Recommendation row itself. Verified: attempting to re-verify a row on an already-COMPLETED mission is correctly rejected (409).

## Duplication fix (self-review) — consolidated three copies of the same mission lookup
**What:** mission_service.py, decision_service.py, and approval_service.py each independently implemented an identical company-scoped Mission lookup — a real violation of this milestone's explicit "no duplicated logic" principle, caught during self-review rather than at write time.
**Resolution:** Consolidated onto mission_service.get_mission as the single source of truth. This required breaking a resulting circular import (mission_service already imported decision_service/tender_service at module level) by deferring those two imports to inside execute_mission() rather than the module top level — a standard, deliberate technique for breaking this kind of cycle, not a workaround being hidden.
**Verified:** server restarts cleanly with no import error; a full smoke test (register → build capability → upload tender → execute → approve) still passes after the refactor.
## B-005 — Freshness idempotency check produced false positives (M9)
**What:** _freshness_already_reflected() originally checked only whether a ComplianceMatrix row's status was in a "compatible" category (REVIEW_REQUIRED/CONDITIONAL for staleness). This is imprecise — a row can be CONDITIONAL for reasons entirely unrelated to freshness (the mock's general humility about ambiguous technical/eligibility matches), which false-positived as "already reflected" and silently skipped a mission that genuinely needed revalidation. Caught via real testing: a backdated project's mission was incorrectly excluded from the first freshness sweep.
**Resolution:** Added a requirement that the specific override marker text decision_engine.py itself writes when it actually applies a freshness override ("cited evidence is expired" / "cited evidence is ... stale") must also be present — combining the structured status check with a targeted, deterministic text check against text the code controls (not fuzzy human-authored prose). Re-tested: first sweep now correctly finds and revalidates the affected mission; a second identical sweep correctly finds zero.

## D-134 — Employee/Project/Certificate mutation and removal are new endpoints (M9)
**What:** No PATCH/DELETE existed anywhere for capability entities before this milestone.
**Resolution:** PATCH/DELETE /api/v1/capabilities/{id}, Administrator-only, restricted to the three MVP entity types with real patchable field whitelists. Same precedent as every other genuine gap filled across this project.

## D-135 — removed_at added to CapabilityMetadataMixin — one migration, all five tables (M9)
**What:** Applying the Database Design's already-frozen Active/Archived/Deleted soft-delete principle to capability entities, which had never needed it until now.
**Resolution:** Single nullable removed_at column, added symmetrically via the shared mixin. list_capabilities() (the one function feeding both M4's graph view and M6/M9's matching candidates) now filters it; find_capability_by_id() deliberately does not, since PATCH/DELETE need to inspect an entity's removed state directly.

## D-136 — decision_service.run_evaluation() gains preserve_mission_state (M9)
**What:** The refined requirement — revalidating a COMPLETED mission must produce a new Recommendation without touching Mission.status/recommendation_id, the original Recommendation, or the human's decision.
**Resolution:** One new keyword parameter, default False (M6/M7/M8 behavior completely unchanged). True skips only the final Mission mutation; every other step (snapshot, recommendation, mappings, compliance rows) happens identically. Also fixed CapabilitySnapshot.snapshot_version, previously hardcoded to 1, to reflect a real count — a latent gap made newly relevant now that multiple snapshots per mission is a first-class scenario.
**Verified exhaustively:** a mission approved (GO) before the triggering capability change kept its Mission row and original Recommendation/ComplianceMatrix/CapabilitySnapshot byte-for-byte identical after revalidation, while a new Recommendation (correctly NOT_GO, reflecting the change) exists and is reachable via the new GET /missions/{id}/recommendations endpoint.

## D-137 — Dependency traversal filters to the mission's CURRENT latest Recommendation (M9)
**What:** CapabilityMapping rows accumulate across every past evaluation of a mission — a naive traversal would flag missions whose dependency on the changed entity is stale/superseded.
**Resolution:** find_affected_missions() traverses CapabilityMapping -> ComplianceMatrix -> Recommendation -> Mission to find candidates, then filters to only those where the mission's latest Recommendation (by generated_at) still actually cites the entity — never scans every Recommendation, and never acts on superseded dependencies.

## D-138 — check-freshness is on-demand, not scheduled (M9)
**What:** No background job/scheduler infrastructure exists anywhere in this project.
**Resolution:** POST /api/v1/capabilities/check-freshness, an explicit sweep using M4's evaluate_freshness unchanged. Real scheduling is future infrastructure work, same category as the async task queue already deferred since the Execution Plan.

---

# M10 — Integration & Consistency Pass (BidOps v1.0)

M10 added no new functionality. It audited the full repository built across M0–M9 for
genuine cross-milestone inconsistencies and fixed only what was actually found —
nothing was changed on the basis of "could be nicer," only on the basis of "this is
inconsistent with the system's own established pattern" or "this is genuinely unused."

## B-006 — GET /api/v1/company/{id} had no authentication at all
**What:** Built in M0, before M1 introduced authentication, and never revisited. Every
other read endpoint built from M1 onward requires `get_current_user`; this one didn't
require anything, and had no company scoping — any authenticated (or even unauthenticated)
caller could retrieve any company's registration details by guessing/knowing its UUID.
**Resolution:** Added `Depends(get_current_user)`, and scoped so a user may only view
their own company — any other `company_id` returns 404, not 403, consistent with the
"never reveal whether something exists for a tenant that isn't yours" principle used
everywhere else since M1.
**Verified:** authenticated self-access returns 200; a second company's token against
the first company's ID returns 404, alongside the same check across five other
endpoints in one continuous integration run.

## Dead code removed — app/orchestration/ (empty since M0)
**What:** An empty package created during M0's initial layer scaffolding, never
populated and never imported anywhere. Mission Orchestrator logic was deliberately
built into `app/services/mission_service.py` at M7 instead — a decision already made
and not being revisited here.
**Resolution:** Removed the empty folder. Confirmed via grep that nothing imported it
before removal, and via a clean server restart afterward.

## Unused imports removed (found via pyflakes, not manual inspection)
- `decision_service.py`: unused `datetime`/`timezone` import, and a genuinely duplicated
  `from app.services import mission_service` line (a leftover from the M8
  duplication-fix that ironically left its own small duplicate behind).
- `mission_service.py`: unused `datetime`/`timezone` import.
- `schemas/tender.py`: unused `datetime` import (only `date` is actually used).
- `models/recommendation.py`: unused `String` import.
**Verified:** `pyflakes app/` clean before packaging; server restarts without error;
full integration re-run confirms no behavior changed.

## Documentation consistency fixes
- `requirements.txt`'s header comment still said "M0 dependencies only" despite having
  grown to cover every milestone through M9 — corrected.
- `.env.example` was missing `STORAGE_ROOT`/`MAX_UPLOAD_SIZE_MB` (both exist in
  `Settings` with real defaults) and lacked the explanatory comments every other
  setting has — added, matching the established pattern.
- **README rewritten in full.** It had accumulated as a per-milestone diary — each
  milestone's "Current Milestone" section overwrote the previous one's, meaning M1,
  M4, M5, M6, M7, and M8 had no documentation at all by the time M9 shipped; only M0,
  M2, M3, and M9 survived. Replaced with one coherent reference covering the full,
  real, current system — no new claims, only documenting what already exists and was
  already verified in prior milestones. Also fixed its stale reference to
  `app/orchestration/` (removed above).

## Verification Performed (M10)
One continuous, unbroken integration run exercising every milestone in sequence for the
first time — previously each milestone was only ever verified in isolation. Register →
authenticated company self-read (the fixed endpoint) → build Certification/Employee/
Project → view capability graph → upload tender → execute mission (Tender Analysis +
Decision Intelligence via M7 orchestration) → verify a HIGH-risk compliance row →
approve (CONDITIONAL_GO, mission COMPLETED) → expire the approved mission's cited
certificate → confirm the mission's historical state (status, original Recommendation,
ComplianceMatrix, and the human's own decision in AuditLog) remained completely
untouched while a new Recommendation (correctly NO_GO) was created and is reachable via
`GET /missions/{id}/recommendations` → company isolation re-confirmed across six
distinct endpoints in one pass, including the newly-fixed company endpoint. Zero schema
drift confirmed both before and after all fixes. `pyflakes app/` clean.

## BidOps v1.0 — Summary
All ten milestones (M0–M10) complete. Auth, company/user management, document storage,
capability extraction with freshness tracking, tender analysis with chunk-and-merge
provenance, decision intelligence with deterministic confidence propagation and
freshness overrides, mission orchestration, human governance with a risk-tiered
verification gate, and event-driven revalidation with full historical immutability —
verified together, as one system, in this milestone, not just individually. The one
standing, explicitly-flagged limitation across the whole project: no real Qwen Cloud
call has been executed anywhere, since this sandbox cannot reach it (D-110) — every
LLM-dependent behavior was verified via a deliberately humble mock that reads real
document text rather than fantasy data. First real Qwen verification is the one
concrete action item for whoever runs this outside the sandbox.

---

## D-139 — M11: Real Qwen Integration — provider robustness, without touching business logic (M11)

**What:** M11's mandate (frozen during Phase 2 Strategy Review): strengthen the Qwen
provider integration's reliability without expanding into prompt engineering, extraction
quality, or business logic — those are M12's job. Three architectural questions were
resolved before implementation began:

1. **Failure surface.** `QwenClient` previously let raw `openai` SDK exceptions escape
   the provider layer — a Provider Independence violation waiting to happen the moment
   any caller started handling them, since that would couple business logic to
   DashScope/`openai`-specific exception types. Resolved by introducing
   `app/agents/llm_exceptions.py`: a small, provider-agnostic exception family
   (`LLMProviderError` base, with `LLMAuthenticationError`, `LLMTimeoutError`,
   `LLMConnectionError`, `LLMRateLimitError`, `LLMProviderResponseError` subclasses).
   `QwenClient.complete()` now translates every `openai` exception it can encounter into
   one of these before it leaves the module. `capability_builder.py`, `tender_analyzer.py`,
   and `decision_engine.py` are unchanged — they still don't handle LLM failures
   explicitly (matching pre-M11 behavior), but if/when they do, they'll only ever need to
   know about this exception family, never about `openai` or DashScope.
2. **Timeout/retry defaults.** Chosen conservative, production-reasonable values rather
   than aggressive ones: 30s request timeout, 3 bounded retries, exponential backoff
   (base 1.0s → waits of 1s/2s/4s). Exponential over fixed-interval because the failures
   worth retrying (rate limits, transient network blips, momentary timeouts) are exactly
   the cases where retrying immediately makes the underlying problem worse, not better;
   giving the provider increasing room to recover is the standard pattern for this
   failure class. All three values are configurable via `Settings`
   (`QWEN_TIMEOUT_SECONDS`, `QWEN_MAX_RETRIES`, `QWEN_RETRY_BACKOFF_SECONDS`), documented
   in `.env.example`, never hardcoded — consistent with every other tunable in this
   codebase (staleness days, chunk size, etc.).
3. **What is never retried.** Authentication failures (`openai.AuthenticationError`) are
   raised immediately, no retry — a bad API key doesn't become valid on attempt two.
   Malformed LLM *response content* (bad JSON, schema-validation failures) is explicitly
   out of scope for this exception surface: that failure happens downstream, in
   `json_utils.parse_json_response` / Pydantic validation, and retrying it would be
   silent prompt-engineering scope creep into M12 territory, not provider robustness.
   Other non-2xx provider responses (`openai.APIStatusError` — arbitrary 4xx/5xx) are
   treated as non-retryable rather than assumed transient, since there's no documented
   DashScope retry contract for arbitrary status codes to justify retrying a request the
   provider has already explicitly rejected.

**Default provider unchanged:** `Settings.llm_provider` still defaults to `"mock"`.
Confirmed intentional during Phase 2 Strategy Review — Qwen is opt-in via explicit
configuration, never a silent default, even after M11's hardening.

**Verified in this sandbox:** unit-level exception-path verification only, using a
hand-rolled fake `openai.AsyncOpenAI` client (no network) —confirmed (a) an
`AuthenticationError` raises `LLMAuthenticationError` immediately with exactly one call
attempt and no backoff wait; (b) a transient `RateLimitError` followed by success
recovers on the second attempt; (c) sustained `RateLimitError`/`APITimeoutError` failures
exhaust exactly `qwen_max_retries + 1` attempts with the expected exponential backoff
intervals before raising the corresponding provider-agnostic exception. `py_compile`
clean on all changed files.

**Not verified in this sandbox, and this milestone is NOT complete until it is:** an
actual live call to Qwen Cloud/DashScope. Per the Constitution's Verification Before
Completion principle and explicit Phase 2 direction, M11 requires successful real
execution of all three LLM call sites — Capability Builder, Tender Analyzer, Decision
Engine — using a real `QWEN_API_KEY` on a machine with real network access to DashScope.
This is the same standing limitation D-110 flagged for the whole of Phase 1, now scoped
down to exactly the one remaining action: run it for real, once, against all three
workflows, and confirm success (or report back whatever the real call surfaces, which
may itself be new information M11's design didn't anticipate).

**Explicitly out of scope for M11 (deferred to M12):** prompt content, extraction
schemas, matching/confidence logic, OCR, MockLLM behavior — none of these were touched,
and none should be inferred as "fixed" by this milestone.

**Definition of Done for M11:** implementation complete (this entry); unit-level
exception-path verification complete (this entry); real DashScope execution across all
three workflows — **outstanding**, owner: whoever runs this locally with a real key.
M11 is not marked complete until that verification is reported back.

---

## D-140 — M11 defect fixes: shared HTTP client + full exception translation (M11)

**Context:** an independent post-implementation review of D-139 (M11) surfaced two
approved defects before real DashScope verification. Both are fixed here, within the
same M11 scope boundary — no prompt, schema, business-logic, or call-site changes.

**Fix 1 — unclosed provider clients (resource leak).** `QwenClient.__init__` previously
constructed a new `AsyncOpenAI` client (and its own `httpx.AsyncClient` connection pool)
on every instantiation. Since `decision_engine.py` calls `get_llm_client()` once per
requirement inside `decision_service.py`'s loop, a single tender evaluation could spin up
dozens of never-closed HTTP clients — free under `MockLLMClient`, a real resource cost
under `QwenClient`. Fixed by caching a single `AsyncOpenAI` instance at module level via
`_get_qwen_http_client()` (`@lru_cache`, the same idiom already used by `get_settings()`
in this codebase, and structurally the same pattern as the module-level `engine` singleton
in `app/core/database.py`). Verified against the installed SDK's own documentation before
implementing: the `openai` package README recommends explicit client instantiation over
the deprecated global-client pattern, and `AsyncOpenAI` wraps `httpx.AsyncClient`, whose
own docstring states it "can be shared between tasks" — i.e., this is the library's
intended reuse pattern, not a workaround. `QwenClient()` can still be instantiated as
often as callers like; only the underlying HTTP client is now a true singleton.

**Fix 2 — incomplete exception translation.** `openai.APIResponseValidationError`
(raised when the SDK's own response-shape validation fails — a real risk against a
third-party "OpenAI-compatible" endpoint like DashScope, not just OpenAI's own service)
is a direct sibling of `APIStatusError`/`APIConnectionError` under `APIError`, and wasn't
individually enumerated in `QwenClient.complete()`'s exception handling — it would have
leaked out of the provider layer as a raw `openai` exception, contradicting this module's
own documented Provider Independence guarantee. Fixed by adding a final
`except openai.OpenAIError as exc` clause (the root of the entire SDK exception
hierarchy) after all existing specific clauses, translating anything not individually
recognized into the existing `LLMProviderResponseError` — no new exception class
introduced — and never retrying it, since an unrecognized failure can't safely be assumed
transient.

**Files changed:** `app/agents/llm_client.py` (both fixes), `app/agents/llm_exceptions.py`
(docstring update to `LLMProviderResponseError` reflecting its catch-all role — no
behavioral or class-name change).

**Verified in this sandbox (offline, no live DashScope call):** re-ran all previously
verified exception-path scenarios (auth immediate-fail, rate-limit-then-recover,
rate-limit/timeout/connection-error each exhausting bounded retries) against a fake
`openai` client — all five behave identically to pre-fix, confirming no regression.
Additionally confirmed: (a) an `openai.APIResponseValidationError` raised by the fake
client now surfaces as `LLMProviderResponseError`, not the raw SDK exception; (b)
instantiating `QwenClient()` five times, with `AsyncOpenAI.__init__` call-counted via
monkeypatch, constructs the underlying client exactly once, and all five instances share
the identical object. `py_compile` clean across the full `app/` tree.

**Still outstanding, unchanged by this entry:** real DashScope execution across all three
LLM call sites (Capability Builder, Tender Analyzer, Decision Engine), per D-139 — M11
remains "Pending Final Verification" until that real run is performed and reported.

---

## D-141 — ADR-001: Gemini adopted as production LLM provider; Qwen frozen (M11.5)

**Context:** Qwen/DashScope (M11, D-139/D-140) is fully implemented and hardened, but real
verification is permanently blocked — DashScope is unreachable for new accounts from this
deployment's region, a platform-level restriction confirmed independently of any repository
defect. Rather than leave the project without a working real provider, Gemini was adopted as
the ADR-001 default production provider. Qwen is **frozen, not deleted**: kept exactly as
implemented and verified (D-140), available if DashScope access is ever restored.

**Implementation:** `GeminiClient` added to `app/agents/llm_client.py`, using Google's native
`google-genai` SDK in Gemini Developer API mode (plain API key from Google AI Studio, not a
GCP service account) — chosen over Gemini's OpenAI-compatibility endpoint so the SDK's own
exception types and retry mechanism could be used directly rather than reinterpreted through
an OpenAI-shaped lens. Exception translation was built from direct inspection of the
installed SDK's `errors.py`, not assumed from similarity to `openai`: `google-genai` raises
exactly two HTTP-status-carrying types (`ClientError` for any 4xx, `ServerError` for any 5xx),
unlike `openai`'s one-class-per-category hierarchy. Retry is the SDK's own built-in
tenacity-based mechanism (configured via `HttpOptions`/`HttpRetryOptions` at construction),
not a hand-rolled loop.

**Verified (real Gemini API, real documents):** Tender Analyzer and Capability Builder both
passed real end-to-end verification via Swagger. Decision Engine reached Gemini successfully
but real verification was blocked by `429 RESOURCE_EXHAUSTED`, then (after disabling internal
retry to remove noise) `503 UNAVAILABLE` — confirmed via repository-wide investigation
(single call site, no duplication, no recursion, correct singleton reuse, correct exception
translation) to be Gemini's free-tier rate-limiting/serving-priority behavior, not a
repository defect. A second API key from a different Google account reproduced the identical
pattern. This is the reason for D-142 below.

**Files changed:** `app/agents/llm_client.py` (`GeminiClient`, `_get_gemini_http_client()`),
`app/core/config.py` (Gemini settings block), `tests/agents/test_llm_client.py` (Gemini
offline coverage, mirroring the Qwen harness).

**Still outstanding at the time of this entry:** Decision Engine real verification — see
D-142, which resolves the blocker via a Vertex AI migration rather than paying cash for
Developer API billing.

---

## D-142 — Gemini migrated from Developer API (API key) to Vertex AI (ADC) — Decision Engine unblocked (M11.5)

**Context:** D-141's Decision Engine blocker (free-tier `429`/`503`) has two possible
resolutions: pay cash to unlock Gemini Developer API billing, or route the same Gemini model
through Vertex AI, which can be funded by already-available Google Cloud trial credits
(₹28,320.75, 90-day expiry). Vertex AI was **not** chosen for technical superiority over the
Developer API — this is an infrastructure/cost decision, not a model-quality one. Secondary
factors: Vertex AI is the infrastructure the roadmap already required for cloud deployment
(M13), so this pulls forward necessary work rather than creating throwaway effort; IAM/service
account authentication is a defensible trust signal for enterprise/government procurement
(a reasonable hypothesis, not yet validated against an actual paying customer).
**OpenRouter remains permanently rejected** for production (a third-party routing vendor is a
harder sell for government/enterprise procurement security review than a direct, named,
auditable vendor) — unaffected by this decision.

**What changed — scope confined entirely to GeminiClient plus its configuration surface.**
Business logic, prompts, JSON schemas, Tender Analyzer, Capability Builder, Decision Engine,
MockLLMClient, and the frozen QwenClient are all untouched.

- `app/core/config.py`: added `GEMINI_AUTH_MODE` ("developer" | "vertex", validated at
  startup — fails fast on an invalid value or on `vertex` mode missing
  `GOOGLE_CLOUD_PROJECT`, never a silent fallback), `GOOGLE_CLOUD_PROJECT`,
  `GOOGLE_CLOUD_LOCATION` (defaults to `us-central1`).
- `app/agents/llm_client.py`: `_get_gemini_http_client()` now branches construction on
  `gemini_auth_mode` — `"developer"` is the exact pre-migration API-key path (kept
  permanently as the local-dev option, since it needs zero GCP setup on a new machine);
  `"vertex"` constructs `genai.Client(vertexai=True, project=..., location=...)`, with no API
  key anywhere in the call — authentication comes entirely from Application Default
  Credentials (ADC). No JSON service-account key file is used in either environment: local
  development uses `gcloud auth application-default login
  --impersonate-service-account=...` (the developer's own Google identity impersonates the
  `bidops-backend` service account, scoped via `roles/iam.serviceAccountTokenCreator` granted
  on that service account specifically, not project-wide); production (once deployed) uses
  the cloud runtime's attached service account identity directly.
- **Auth-exception audit, scoped narrowly per the migration review:** the existing
  `ClientError`/`ServerError`/`UnknownApiResponseError`/`httpx` exception handling was built
  and verified against Developer-API failures and is unchanged — re-reviewing it was
  explicitly out of scope, since it's the same SDK error module regardless of auth mode. The
  one genuinely new surface is credential acquisition/refresh, raised by `google-auth`
  (not `google-genai`) before any request reaches Google's servers:
  `google.auth.exceptions.DefaultCredentialsError` (no ADC found at all) and
  `google.auth.exceptions.RefreshError` (ADC found, but a refresh/impersonation call failed —
  e.g. the token-creator grant was revoked) are now caught in `GeminiClient.complete()` and
  translated into `LLMAuthenticationError`, never retried, matching the existing policy for
  `ClientError(401/403)`.
- **IAM (least privilege):** `bidops-backend` service account holds `roles/aiplatform.user`
  only (Google's current UI label: "Agent Platform User") — permission to call existing
  Vertex AI resources (`generateContent`), not to create/modify/delete Vertex infrastructure.
  No `aiplatform.admin`, `editor`, or `owner` granted to the service account.
- **Region:** `us-central1` for this initial migration. The `us-central1` vs `asia-south1`
  (Mumbai)/`asia-south2` (Delhi) decision is **deliberately deferred** until after this
  migration is verified end-to-end — region is a per-call runtime parameter, not something
  locked into the project or service account, so benchmarking it now would introduce a second
  unverified variable alongside the auth migration itself. Must be revisited before production
  deployment (M13) given BidOps's Indian government/enterprise target market and both regions'
  MeitY empanelment.
- **Offline verification:** `tests/agents/test_llm_client.py` extended with construction-branch
  tests (developer vs vertex), settings-validation tests (invalid mode, missing project both
  fail fast), and the two new auth-exception-mapping tests — all using fake exceptions/fake
  clients, zero real GCP credentials required. Two pre-existing tests
  (`test_settings_gemini_defaults`, and the developer-mode construction test) were found
  during this work to implicitly depend on no real `.env` file existing in the working
  directory — true in CI, false for any actual developer checkout, since `LLM_PROVIDER=gemini`
  has been in `.env` since D-141. Fixed by constructing `Settings(_env_file=None)` where the
  test's intent is to verify the code's built-in default rather than the local environment.
- **Standalone infrastructure verification** (independent of the BidOps backend, so that a
  future failure can be triaged as "cloud infra problem" vs "backend problem"): real ADC
  auth chain (gcloud CLI → login → impersonation → access token) verified; a real Vertex AI
  Gemini call verified (plain text, then structured JSON matching a Decision-Engine-shaped
  schema — the JSON case specifically, not just plain text, because BidOps's actual pipelines
  depend on structured output, not conversational text). Kept as `scripts/vertex_smoke_check.py`
  — deliberately not named `test_*.py`/`*_test.py` so pytest never auto-collects it (a stray
  `test_gemini.py`/`test_vertex.py`/`test_vertex_json.py` had been created at the repo root
  during this exploration and were found, during this same review, to break `pytest`
  collection entirely — `genai.Client(...)` was called at module import time in those files,
  meaning even `pytest --collect-only` attempted a real network call. Removed from the repo).

**Security finding during this review, resolved:** `test_gemini.py` (one of the stray root
scripts above) contained a real Gemini Developer API key hardcoded in plaintext. It was not
inside a git repository (no `.git` found in this checkout) and was a different key from the
one in `.env`, but should be treated as compromised regardless, since the file had already
left this machine via a shared archive — **rotate/revoke that specific key in Google AI
Studio.** `.gitignore` updated to explicitly exclude root-level `test_*.py` and `login.txt`
(a second stray file containing plaintext test-account credentials, also removed) as a
guard against this recurring.

**Not changed by this migration:** OpenAI provider work (comes after Gemini/Vertex closure,
unchanged execution order), removal of Developer API mode (explicitly retained for local dev).

**Still outstanding at the time of this entry, owner: whoever runs this with real Vertex AI
credentials:**
1. Google Cloud Billing budget/alert — confirm configured before any further real Vertex
   spend (90-day credit window).
2. Real verification, in order: authentication-failure path (e.g. temporarily revoke the
   impersonation grant, confirm `LLMAuthenticationError` actually surfaces) → Tender Analyzer
   → Capability Builder → Decision Engine (the original blocker, and therefore the primary
   success criterion for this milestone).
3. Flip `GEMINI_AUTH_MODE` default to `"vertex"` in the repository's own `.env`/deployment
   config once all three pipelines above pass for real (already flipped in this checkout's
   local `.env` ahead of that real verification — track this as **provisional**, not yet
   backed by a real Decision Engine pass, until item 2 is complete).
4. `us-central1` vs `asia-south1` region benchmark, before production deployment (M13).

---

## D-143 — BidOps_Final: canonical repository consolidation; OpenAI adopted as operational reference implementation (Milestone 1–3)

**Context:** Two lineages had diverged from this repository: the startup repository (this
one — Qwen frozen, Gemini/Vertex as the strategic provider, offline-verified but never
executed against real GCP) and a separately-built OpenAI Build Week submission (Qwen/Gemini/
Vertex replaced entirely with a single `OpenAIClient`, verified end-to-end against real
documents including the Decision Engine — the one pipeline Vertex has never completed for
real). Per explicit founder direction: there is only ever one BidOps going forward. Both
source repositories become permanent, read-only historical references; this repository
(`BidOps_Final`) is the sole canonical codebase from this point on.

**What was actually true, verified directly (not assumed) before this consolidation:** a full
recursive diff of both backends found only 7 files genuinely differed
(`llm_client.py`, `llm_exceptions.py`, `prompts/certification.py`, `core/config.py`,
`core/database.py`, `main.py`, one unused import in `decision_service.py`) — every model,
schema, service, and API route was byte-identical. The offline provider-layer test suite
(33 tests) was independently re-run in a clean environment and confirmed passing before any
merge work began.

**Provider strategy decision (founder-approved, reversing an earlier draft directive that had
named Vertex as default):** OpenAI is the operational reference implementation — the only
provider with a real, verified, end-to-end Decision Engine run. Vertex AI (via Gemini,
`GEMINI_AUTH_MODE=vertex`) remains the strategic long-term provider for the reasons already
recorded in D-142 (IAM/buyer-trust argument, GCP credit economics) but is not the default
until it clears the same real-verification bar. This is an evidence-based reversal, not a
rejection of the Vertex strategy — recorded explicitly per this project's own "assumptions
must be labeled as assumptions, evidence preferred over intuition" standard.

**What changed:**
- `app/agents/llm_client.py`: `OpenAIClient` added alongside the existing `QwenClient` and
  `GeminiClient` (Developer + Vertex auth modes) — not a replacement of either, unlike the
  OpenAI Build Week repository's own version, which had removed them. All three real clients
  plus `MockLLMClient` now coexist behind the unchanged `LLMClient` Protocol and
  `get_llm_client()` factory. `OpenAIClient`'s implementation mirrors `QwenClient`'s
  hand-rolled retry loop (same underlying `openai` SDK) and carries forward one real
  production lesson from OpenAI Build Week: GPT-5-series models reject any non-default
  `temperature` value outright, so none is sent.
- `app/core/config.py`: added `openai_api_key` / `openai_model` (`gpt-5.6`) /
  `openai_base_url` / retry-and-timeout settings, alongside the complete, unmodified Qwen and
  Gemini/Vertex settings blocks. Added `allowed_origins` (Milestone 4) and a new fail-fast
  validator, `_validate_secret_key` (Milestone 5): refuses to start if `APP_ENV` is anything
  other than `"development"` and `SECRET_KEY` is still the shipped default — closing a gap
  that had been flagged, but not fixed, across two prior sessions' handoff documents. The
  existing `_validate_gemini_auth_mode` validator is unchanged.
- `app/main.py`: CORS origin changed from a single hardcoded value (this repo's
  `localhost:5173`-only, or the OpenAI Build Week repository's hardcoded Vercel demo URL —
  neither was right for a multi-environment canonical product) to an env-driven
  `ALLOWED_ORIGINS` list, defaulting to the local dev origin if unset.
- `app/agents/prompts/certification.py`: adopted the OpenAI Build Week repository's real
  extraction-quality improvement — deriving `certification_name` from a document's title/
  heading when no field is explicitly labeled "Certificate Name," discovered against real
  certificate documents during that repository's own testing.
- `app/services/decision_service.py`: removed one dead `import traceback`, matching the
  OpenAI Build Week repository's own cleanup of the same line.
- `tests/agents/test_llm_client.py`: merged. This repository's 33 tests (Qwen/Gemini/Vertex/
  Mock/factory/config coverage) plus the OpenAI Build Week repository's OpenAI-specific tests
  (ported, using the same fake-client idioms already established for Qwen) plus 3 new tests
  for the Milestone 5 `SECRET_KEY` validator — 48 tests total, all passing.

**Explicitly not brought forward:** the OpenAI Build Week repository's `allow_credentials=False`
CORS setting (a regression from this repository's `True`) and its hardcoded single-origin CORS
value — both superseded by the new env-driven `ALLOWED_ORIGINS` design instead of copied as-is.
`HackathonBanner.tsx` and its `Layout.tsx` wiring were excluded from the frontend copy as
hackathon-specific branding, not product.

**Verified in this session (offline, this sandbox has no live Postgres/GCP/OpenAI network
access):**
- Full recursive diff of both source backends (7 genuinely differing files, confirmed above).
- Merged offline test suite: 48/48 passing (proxy environment variables stripped — this
  sandbox's own `HTTP_PROXY`/`ALL_PROXY` setup breaks `httpx` client construction unrelated to
  application correctness, same finding as the prior session's Vertex-only 33/33 run).
- `grep` across the full `app/` tree: zero imports of `openai` or `google` outside
  `llm_client.py` — Provider Independence holds structurally, not just by convention.
- `pyflakes app/`: clean, zero warnings.
- `python -c "from app.main import app"`: imports cleanly, 36 routes registered, with the real
  `.env` loaded (`LLM_PROVIDER=openai` resolves to `OpenAIClient` via the factory, confirmed by
  `isinstance` check).
- `alembic history`: all 4 migrations chain correctly, `<base> → … → 2ae90e7010e9 (head)`,
  matching the source repository exactly.
- Frontend: `tsc --noEmit` clean (exit 0) against the copied `frontend/src`, which already
  carries the `tender_id` response-contract fix and the Run Full Analysis orchestrator wiring
  from the prior session.

**Not verified in this session, and explicitly not claimed as done:** `alembic upgrade head`
against a real running Postgres instance (no Postgres available in this sandbox); any real
network call to OpenAI, Gemini Developer API, or Vertex AI (no credentials configured for
live calls in this sandbox, and Vertex AI specifically still requires real on-GCP verification
per D-142's outstanding items, unchanged by this entry).

**Files carried forward unchanged (verified byte-identical or functionally identical to their
source):** all models, schemas, services (except the one-line `decision_service.py` cleanup
above), API routes, `llm_exceptions.py`, `core/database.py`, `core/security.py`,
`core/storage.py`, all Alembic migrations, `requirements.txt` (already included both `openai`
and `google-genai` — no new dependency was needed for `OpenAIClient`).

---

## D-144 — POST /tenders/upload and POST /capabilities/build given real response schemas (Milestone 6)

**Note on numbering:** this entry was first logged as "D-140" because, at the time, D-112
through D-116 already existed twice each in this log — once from the original M11/M11.5/
consolidation era (below the `---` divider after M10) and once from earlier in the file (M6 of
the original build, pre-M10) — a pre-existing collision, not introduced here, and D-140 was
simply the next number not already in use. That duplication was flagged in this entry for
founder visibility and, per explicit founder direction immediately following M6's approval, was
then normalized in a dedicated, documentation-only pass: every decision in this file (D-101
onward) was renumbered sequentially in chronological/file order, closing the one pre-existing
gap (a former "D-107" never existed) and removing every duplicate, with no content, history, or
conclusion changed — only IDs. This entry's own number changed from D-140 to D-144 as a direct
result of that same pass. Every cross-reference in this file and across the rest of the
repository (`README.md`, `BACKLOG.md`, backend `README.md`, `.env.example`, and inline code
comments citing a specific decision) was updated to match, resolved individually against which
specific decision each reference actually meant — not a blind find-and-replace, since the old
duplicate IDs could not otherwise be told apart.

**What:** M6's audit of `BACKLOG.md`'s carried-forward concern — both `POST /tenders/upload`
and `POST /capabilities/build` were declared `response_model=dict` / bare `-> dict`, so the
OpenAPI spec described both as `additionalProperties: true` rather than a named schema. This
is the same defect class as the `tender_id`/`id` frontend bug fixed in the prior session
(D-143 background): a response shape that exists only by convention, not by declaration, is
free to drift from what a caller assumes without either side finding out until runtime.

**Audit conclusion, evidence-based, checked against actual frontend usage before touching
anything:**
- `POST /tenders/upload`: backend returns `{"tender_id": ..., "mission_id": ...}`;
  `frontend/src/pages/TenderUpload.tsx` reads `res.tender_id` and `frontend/src/api/types.ts`'s
  `TenderUploadResponse` already declares both fields correctly — this is the fix already
  verified in the prior session. No live bug remained here; only the backend-side typing gap.
- `POST /capabilities/build`: backend returns `{"entity_type": ..., "entity": ...}`;
  `frontend/src/pages/Capabilities.tsx`'s `handleBuild()` calls `buildCapability()` but never
  reads its return value — it awaits the call purely as a success/failure signal, then calls
  `refresh()` (backed by the separately, properly-typed `getCapabilityGraph()`) to update UI
  state. **No live contract mismatch exists here**, because nothing in the frontend depends on
  this endpoint's response shape. This is a real finding, not an assumption: confirmed by
  reading both the router and every call site before concluding.

**Resolution — fixed rather than merely logged, per this repository's own Technical Debt
Policy** (`docs/ENGINEERING_DIRECTIVE.md`): "Fix now" applies to changes that are cheap,
isolated, and close a bug class already proven to recur — exactly this case, given the
`tender_id` precedent. Both endpoints were also the last two hand-rolled `dict` returns in an
otherwise fully-typed API (every other router already returns a declared Pydantic
`response_model`), so this also closes a real inconsistency, not just a hypothetical risk.
- Added `TenderUploadResult` (`app/schemas/tender.py`): `tender_id: uuid.UUID`,
  `mission_id: uuid.UUID`. Wired as `response_model` on `POST /tenders/upload`; wire format is
  byte-identical to before (UUID serializes to the same JSON string `str(...)` produced), so no
  frontend change was required or made.
- Added `CapabilityBuildResult` (`app/schemas/capability.py`): `entity_type: CapabilityEntityType`,
  `entity: CertificationRead | EmployeeRead | ProjectRead`. The union is deliberately scoped to
  exactly the three M3 MVP entity types in `READ_SCHEMAS` (not all five `CapabilityEntityType`
  members — `equipment`/`financial_record` are not reachable through this endpoint and were
  never in `READ_SCHEMAS`). Wired as `response_model` on `POST /build`.

**Verified before considering this done:**
- Standalone script (not committed) constructed real `CertificationRead`/`EmployeeRead`/
  `ProjectRead` instances — including a `ProjectRead`, whose only required fields are the common
  base ones, making it the actual risk case for union-type misidentification — and confirmed
  Pydantic v2's default union validation preserves the exact concrete type both in-process and
  across a full JSON serialize/reparse round trip. No discriminator field was needed.
- `app.main.app.openapi()` regenerated after the change: both endpoints now show a named
  `$ref` component schema instead of `additionalProperties: true`; `CapabilityBuildResult`'s
  `entity` field renders as the expected three-member `anyOf`. Full schema still builds clean
  (28 paths, 53 component schemas, no errors).
- Existing offline test suite (`tests/agents/test_llm_client.py`, 48 tests — unrelated to this
  change but the only automated regression coverage this repository has) still passes
  unchanged: 48/48.
- `frontend`: `tsc --noEmit` clean — confirms the wire-format-unchanged claim above rather than
  just asserting it.
- `py_compile` clean on all four changed/added files.

**Not built, deliberately:** no test file for these two routers specifically — this repository
has no FastAPI `TestClient`/integration-test harness yet (only the LLM provider offline unit
suite exists), and building one is a real, separate scope decision (fits naturally under M8's
"broader test coverage"), not something to improvise as a side effect of a typing fix.

**Discovered, not fixed — flagged for a founder decision:** `GET /capabilities/{entity_id}`
(`app/api/v1/capabilities.py`) has the identical `{"entity_type": ..., "entity": ...}` bare-dict
pattern, sibling to the `POST /build` issue just fixed, but was not named in the original audit
scope (`BACKLOG.md` named only the two upload endpoints) and was not touched here, to keep this
change incremental and reviewable rather than expanding scope mid-milestone without checking in
first.

## D-145 — Evaluation response extended with source_page and evidence_source

**What:** `EvaluationResponse` (`GET /evaluation/{id}`, `POST /evaluation/run`,
`GET /recommendations/{id}`) gains two additive fields: `ComplianceMatrixEntryRead.source_page`
(the tender page a requirement's clause came from) and `ComplianceMatrixEntryRead.evidence_source`
(a new `EvidenceSourceRead`: the resolved company record — certification/employee/project/
equipment/financial-record name — and its source document, resolved from the existing
`evidence_reference` → `CapabilityMapping` → entity table chain). `GapAnalysisEntry` also gains
`source_page`. No existing field removed or retyped; both are optional and default to `None`.

**Why:** Triggered by implementation work against `docs/DESIGN_SYSTEM.md` §10, which names the
Decision Screen's signature experience as a four-step chain: Recommendation → Evidence → Source
Clause → Company Document. The first two steps already existed in the API
(`recommendation`, `compliance_matrix[].supporting_evidence`); the last two — the specific tender
clause and the specific company record that ground a recommendation — existed in the database
(`Requirement.source_page`, `CapabilityMapping` → entity tables) but were never surfaced through
`EvaluationResponse`. Building the signature screen without them would mean fabricating
placeholder text for "why," which directly violates `PRODUCT_CONSTITUTION.md` §7's Evidence
First principle: "every recommendation traceable to explicit evidence." This is exposing
already-modeled data, not new architecture — no new table, no new persisted concept.

**Alternatives considered:** (1) Leave the Decision Screen at Recommendation → Evidence only,
holding the last two steps until a pilot customer asks for them. (2) Return the raw
`evidence_reference` UUID and resolve it client-side. (3) Resolve to a human-readable label
server-side, as built.

**Why rejected:** (1) would ship the one screen `DESIGN_SYSTEM.md` explicitly calls the
product's signature/most-differentiating screen in a visibly incomplete state, when the
underlying data already exists — the founder's explicit call ("if you think this will help the
startup and improve it then please implement it") was to close the gap now rather than defer it.
(2) would require the frontend to know about `CapabilityMapping` and five separate entity
tables, leaking a backend persistence detail across the API boundary for no benefit. (3), the
approach taken, keeps the frontend contract simple (one label, one optional document name) and
keeps entity-resolution logic in one place.

**Implementation:**
- `app/schemas/decision.py`: new `EvidenceSourceRead` (`entity_type`, `label`,
  `source_document_id`, `source_document_name`); `source_page: int | None = None` added to
  `GapAnalysisEntry`; `source_page` and `evidence_source` added to `ComplianceMatrixEntryRead`
  (both default `None`, since neither lives on the `ComplianceMatrix` ORM row and can't be
  populated via `model_validate()`'s `from_attributes`).
- `app/services/decision_service.py`: new `resolve_evidence_sources()` — collects every
  non-null `evidence_reference` from a mission's compliance rows, resolves each
  `CapabilityMapping` to its polymorphic entity (reusing the same
  `capability_entity_type`/`capability_entity_id` shape `revalidation_service.py` already
  traverses, just resolved to a display label instead of used for dependency lookup), then to
  that entity's source `Document.file_name`. Tolerant of an entity that no longer resolves
  (skips it) rather than raising — a resolution gap must never break the evaluation response.
- `app/api/v1/evaluation.py`: `_build_response()` now takes `db`, calls
  `resolve_evidence_sources()` once per request, and attaches `source_page`/`evidence_source` to
  each row via `model_copy(update=...)` (since `model_validate()` alone can't reach across the
  join). All three call sites (`POST /evaluation/run`, `GET /evaluation/{id}`,
  `GET /recommendations/{id}`) updated identically.
- `frontend/src/api/types.ts`: `EvidenceSourceRead` added; both new fields added to
  `ComplianceMatrixEntryRead`/`GapAnalysisEntry`. `complianceMerge.ts` required no change — it
  already spreads the full compliance-matrix entry, so the new fields pass through automatically.
- `frontend/src/pages/Evaluation.tsx` (`MatrixRow`): the "View evidence" disclosure per
  requirement row now renders the full trail — Evidence / Source clause (page N) / Company
  record (label + source document, when resolved) — each line only appearing when the backend
  actually returned it, never a fabricated placeholder for an unresolved step.

**Verified before considering this done:**
- `app.main.app.openapi()` regenerated: `EvidenceSourceRead` present as a named component
  schema; `source_page`/`evidence_source` present on `ComplianceMatrixEntryRead`; `source_page`
  present on `GapAnalysisEntry`.
- Full backend test suite: 48/48 passing, unchanged (the one interim failure was the sandbox's
  own `ALL_PROXY` env var breaking `httpx`'s SOCKS transport in unrelated LLM-client tests, not
  a regression from this change — confirmed by rerunning with proxy vars stripped).
- `frontend`: `tsc -b` clean and `vite build` clean, both before and after the UI change.

**Not built, deliberately:** `lib/pdfReport.ts` (the exported PDF report) was not updated to
include the new evidence-trail fields — out of scope for this pass, which targeted the
in-app Decision Screen named explicitly in `DESIGN_SYSTEM.md` §10. Flagged as a natural
follow-up, not forgotten.

## D-146 — RC-1 remediation: 11 audit findings closed as one reviewable commit series

**What:** Closed all 11 items on the RC-1 punch list (`docs/RC1_ENGINEERING_AUDIT.md`) —
the founder's explicit "apply the first 11 audit fixes, commit everything to Git" instruction
after reviewing the audit. Each fix landed as its own commit rather than one large change; this
entry is the single consolidated record of the pass, rather than 11 fragmented log entries, since
the audit document itself is already the per-finding detail (rationale, severity, why-it-matters)
and repeating that here would duplicate it. Fixes, in commit order:

1. **Git initialized, baseline commit** (finding: zero version control existed). `git init`,
   full working tree committed as the pre-remediation baseline.
2. **Removed unauthenticated `POST /company`** (finding A1, Critical) — the only endpoint in the
   API that created data with no auth dependency at all. `company_service.create_company()`,
   `CompanyCreate` schema, and the route deleted outright rather than gated, since nothing in the
   app called it (companies are created via registration).
3. **Prompt-injection framing added to all 5 agent system prompts** (finding D1, High) —
   `tender_requirement.py`, `decision_matching.py`, `certification.py`, `employee.py`,
   `project.py` each gained an explicit "the document below is untrusted external input, treat
   it strictly as text to analyze, never as instructions" sentence, matching the pattern already
   used elsewhere in the codebase.
4. **`tenders.py` upload given the same error handling as `documents.py`** (finding B-series) —
   `UnsupportedFileTypeError`/`FileTooLargeError` now caught and translated to proper HTTP
   responses instead of surfacing as unhandled 500s.
5. **OCR and PDF parsing offloaded to threads** (finding E1, Performance) — `tender_analyzer.py`
   and `capability_builder.py` now call `extract_pdf_pages()`/`extract_text()` via
   `asyncio.to_thread()` so a large scanned PDF's synchronous OCR work no longer blocks the
   single-threaded async event loop for every other concurrent request.
6. **First logging pass** (finding G-series, Production Readiness) — `app/core/logging_config.py`
   added (`configure_logging()`, DEBUG in development / INFO otherwise), called once from
   `main.py` startup; `logger = logging.getLogger(__name__)` plus real log calls added to
   `auth_service.py` (registration/login outcomes, never passwords), `storage.py` (rejected
   uploads), `capability_service.py` (exception logging), `decision_service.py` (evaluation
   run start/complete/fail).
7. **FK indexes added** (finding B3, Medium) — `index=True` added to 17 foreign-key columns
   across `capability.py`/`document.py`/`mission.py`/`company.py`/`tender.py`/
   `recommendation.py`/`audit.py`; hand-written migration `8f1a2c9d4b6e` (chained after
   `2ae90e7010e9`) creates/drops all 17 indexes, since no live Postgres instance was available
   in this environment to autogenerate it.
8. **Archived stale `CONSTITUTION.md`** (finding A2) — moved to
   `docs/archive/CONSTITUTION_v1_SUPERSEDED.md` with a banner explaining why (its own frozen
   roadmap named "Alibaba Cloud Deployment," which no longer reflects reality, and its
   precedence order predates `PRODUCT_CONSTITUTION.md`/`DESIGN_SYSTEM.md` entirely) and pointing
   to the documents that actually govern the project now.
9. **Deleted `_test.txt`** (finding: stray root-level file with no purpose).
10. **Accessibility pass** (finding C1, Medium) — `Layout.tsx`'s sidebar/nav/main landmarks and
    account menu given `aria-label`s; `Menu.tsx` given `aria-haspopup`/`aria-expanded`/an
    accessible-name prop; `LogoMark`'s decorative SVG and the avatar initial both marked
    `aria-hidden="true"` so a screen reader doesn't announce redundant information already
    conveyed by adjacent text.
11. **Unified empty-state components** (finding C2, Low) — `Evaluation.tsx`'s
    "not evaluated yet" state and `TenderDetail.tsx`'s "ready to analyze" state each hand-rolled
    their own icon/title/description/action markup; both swapped to the shared `EmptyState`
    component already used by Dashboard/Missions/Documents/Capabilities/Reports, for visual and
    structural consistency. No behavior change.

**Why:** The RC-1 audit rated these findings Critical-to-Low across security, performance,
accessibility, and consistency. The founder reviewed the audit, agreed with 9.5/10 of it (with
one severity note on logging, upgraded here from Medium to High per that discussion), explicitly
declined to treat Docker/CI/on-delete-cascade-behavior/dashboard-query-batching as blockers for
this pass, and gave the exact sequence to execute next — applying these 11 fixes and committing
was the first two items of that sequence.

**Alternatives considered:** Bundling all 11 into a single commit. **Why rejected:** the audit's
own recommendation (and the founder's git-history complaint — the repo had zero commits before
this pass) was that each change should land as its own reviewable, revertible unit; a single
giant commit would have reproduced the exact lack-of-history problem being fixed.

**Verified before considering this done:**
- Backend: `python -m pytest -q` — 48/48 passing (proxy env vars stripped, see D-145's note on
  the same sandbox quirk).
- `backend/scripts/verify_evidence_trail.py` — 19/19 PASSED, confirming the RC-1 changes
  (particularly the FK-index migration and logging additions) didn't regress the evidence-trail
  pipeline verified in D-145.
- `python -c "import app.main; ..."` — full import sweep across every module touched by this
  pass (`company`, `tenders`, `evaluation`, `documents`, `company_service`, `decision_service`,
  `capability_service`, `auth_service`, `logging_config`, `storage`, `tender_analyzer`,
  `capability_builder`) — no import errors, startup log line confirms `configure_logging()`
  runs.
- `alembic history` — single linear head at `8f1a2c9d4b6e`, no branching, chain intact from
  `265e4dc23a06` through all five migrations.
- Frontend: `tsc -b` clean, `vite build` clean, checked after every individual fix that touched
  frontend code (fixes 10 and 11), not just once at the end.
- Each of the 11 fixes above has its own commit in `git log`, in the order listed.

**Not built, deliberately (per explicit founder scope call, not oversight):** Dockerfile/
docker-compose, CI pipeline, explicit `ondelete` cascade behavior audit, and dashboard N+1 query
batching — all flagged in the audit but the founder judged them non-blockers for this pass.
`pip-audit` dependency CVE scanning could not be run (the tool failed to bootstrap in this
sandbox — no network access to upgrade its own build environment); this remains an unverified
area, stated as such rather than assumed clean. Real deployment (backend/frontend), testing with
real tender PDFs, and pilot-user observation are the next steps in the founder's stated sequence
but require real infrastructure/customer access outside what this pass could execute.

## D-147 — Brand palette reversed: deep blue → indigo/violet gradient (supersedes DESIGN_SYSTEM.md v1.0)

**What:** Replaced the frozen deep-blue `--primary` token and flat-fill `LogoMark` with an
indigo-to-violet gradient, across the entire app (landing page, Dashboard, sidebar, buttons,
Login split panel), not just the marketing landing page being built in this same session. New
tokens added: `--logo-gradient-from` (indigo-500), `--logo-gradient-to` (violet-600, same hue
also used as the new flat `--primary`). `--brand` (Login panel dark surface) recolored to a deep
violet-charcoal to match. `--brand-accent` (muted teal, evidence/traceability emphasis on the
Decision Screen) is unchanged — it serves a distinct semantic purpose, not brand identity, and
this decision doesn't touch it.

**Why:** The founder supplied a new official logo image (indigo/violet gradient monogram) and
explicitly asked for it, and its color, to become "the official color of our entire SaaS," used
everywhere. This directly reverses DESIGN_SYSTEM.md v1.0's explicit rule ("no purple, no violet,
no second competing accent... deep blue is the primary/interactive color"), which itself was a
deliberate rejection of an earlier indigo/violet identity. Flagged this conflict to the founder
before touching anything, including that it would affect the entire authenticated app, not just
the landing page (which had a separate, narrower "UI freeze lifted" exception already agreed for
this session) — founder explicitly confirmed applying it everywhere, formally superseding v1.0.

**Alternatives considered:** Using the new logo only on the public landing page while leaving the
authenticated app on the old deep-blue system, so the internal product and the marketing site
would carry two different identities. **Why rejected:** explicitly declined by the founder when
asked — a split identity was called out as worse than a full, consistent switch.

**Implementation note:** `LogoMark`'s SVG structure (rounded badge, "B" glyph, sparkle accents)
is unchanged — only its fill switched from a flat `--primary` color to a `<linearGradient>`
matching the new tokens, with the gradient `id` generated per-instance via `useId()` since the
mark renders multiple times on the same page (sidebar, navbar, footer, login) and a hardcoded
duplicate SVG gradient id can misbehave across repeated inline `<svg>` elements. This is a
faithful color/spirit match to the founder's reference mark, not a pixel-traced reproduction of
its more elaborate illustrated glyph — reproducing that exactly would mean hand-authoring a
materially more complex multi-shaded path than the simple rounded-badge treatment already used
everywhere the mark appears in the product.

**Verified before considering this done:**
- Frontend: `tsc -b` clean, `vite build` succeeds.
- Confirmed the compiled CSS actually contains both new gradient stop-color declarations
  (`grep`'d the built `dist/assets/index-*.css` output directly, not just eyeballed the source).
- Checked visually via screenshots from the founder after each change (spacing/layout passes
  before this one).

**Not done in this pass:** No static logo/favicon image assets (PNG/ICO/SVG files in `public/`)
exist to swap — the mark is rendered entirely as inline SVG via `LogoMark`, so there was nothing
additional to replace there. If real exported brand assets are produced later, they should
replace the inline SVG the same way the previous flat-fill version's own comment anticipated.

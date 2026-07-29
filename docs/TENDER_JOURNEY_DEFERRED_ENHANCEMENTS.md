# Tender Journey — Deferred Enhancements Log

Append-only. Per `TENDER_JOURNEY_IMPLEMENTATION_PLAN.md` §0's scope
discipline rule: anything that surfaces during implementation but isn't
in the approved plan gets logged here, not built. Each entry: which phase
surfaced it, what it is, why it wasn't just done anyway.

## Phase 1

- **`frontend/src/lib/pdfReport.ts:98`** — the generated PDF report has its
  own `"AI Decision"` label (`["AI Decision", recommendationLabel(...)]`),
  in the same spirit as the two strings Phase 1 changed. Not in the
  approved Phase 1 file list (`Evaluation.tsx`, `Reports.tsx`,
  `TenderDetail.tsx`) and PDF output wasn't reviewed against the
  vocabulary rule before this plan was approved, so left untouched rather
  than assumed in scope. Trivial fix whenever explicitly approved — same
  one-word label swap as the two already made.
- **`frontend/src/pages/Landing.tsx:70`** and
  **`frontend/src/components/landing/landingData.ts:510`** — both say
  "Explainable AI Decisions" as marketing copy (plural, tagline usage, not
  the authenticated-app "AI Decision" label context the design doc's
  vocabulary rule addresses). Confirmed out of scope, not logged as a
  deferred enhancement — the Tender Journey design doc's philosophy
  governs the authenticated product experience, not the public marketing
  page, and this phrase reads differently in a tagline than as a UI label
  implying the AI made a choice. Noting the distinction here so it isn't
  re-flagged as an oversight later.

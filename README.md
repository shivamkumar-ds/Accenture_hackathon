# BidOps

Enterprise procurement decision-intelligence platform. Reads a tender, cross-references it
against an organization's own capability evidence, and returns a structured, evidence-backed
Proceed / Do Not Proceed / Conditional recommendation — not a document summary, not a chat
transcript.

This is **BidOps_Final**, the single canonical codebase. There is no separate Vertex, OpenAI,
Qwen, or Hackathon edition — see `docs/ENGINEERING_DIRECTIVE.md` for why, and
`backend/99_DECISIONS_LOG.md` (entry D-143) for exactly how this repository was consolidated
from its two prior lineages.

## Structure

- `backend/` — FastAPI + PostgreSQL. See `backend/README.md` for setup, configuration, and
  the full request-to-recommendation workflow.
- `frontend/` — React + TypeScript + Vite. Dashboard, Documents, Capabilities, Tender
  Workspace, Reports.
- `docs/` — the frozen product/architecture specification (`00_Project_Context.md` through
  `11_Risk_Assessment.md`), the engineering `CONSTITUTION.md`, and
  `ENGINEERING_DIRECTIVE.md` (the standing founder-to-engineering direction for this
  project).
- `BACKLOG.md` — real, open, unresolved product/engineering items — not a wishlist, a record
  of what's actually still missing.

## Where things stand

- **OpenAI** — operational reference implementation. Verified end-to-end, including the
  Decision Engine.
- **Vertex AI (Gemini)** — strategic long-term provider. Implemented and offline-tested;
  real on-GCP verification is deployment-gated (needs `gcloud`/ADC and network access no
  development sandbox in this project's history has had).
- **Qwen** — frozen. DashScope is unreachable for new accounts from every region tried so
  far; kept working, not deleted.

See `backend/99_DECISIONS_LOG.md` for the complete reasoning trail behind every decision in
this repository, in order — the actual source of truth for *why*, not just *what*.

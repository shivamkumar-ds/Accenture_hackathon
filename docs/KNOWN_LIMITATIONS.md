# BidOps — Known Limitations

Not technical debt, not a backlog — a record of what BidOps deliberately does not do yet, and
why, so that revisiting one of these later starts from "here's the existing reasoning" instead
of reopening a decision from scratch. Each item names the real constraint and, where one
exists, the decision log entry it traces back to.

## Provider & AI

- **Vertex AI has never completed a real, verified Decision Engine run.** Tender Analyzer and
  Capability Builder passed real verification against Vertex; the Decision Engine specifically
  has not, and is gated on a real GCP-connected deployment environment (`gcloud`/ADC, real
  network access) that no development sandbox in this project's history has had. OpenAI is the
  operational default until this clears — see `99_DECISIONS_LOG.md` D-141, D-142, D-143, and
  `docs/ENGINEERING_DIRECTIVE.md`'s M7 gating.
- **Provider selection is a single, global, env-level setting** (`LLM_PROVIDER`), not
  per-organization or per-user. An org-level Settings UI for this is scoped as real, near-term
  work but not built.
- **Qwen (DashScope) is frozen, not deleted.** Unreachable for new accounts from every region
  tried so far — a platform restriction, not a repository defect.
- **Vertex AI region is undecided.** `us-central1` is the current default; the
  `us-central1` vs. `asia-south1`/`asia-south2` decision (relevant given BidOps's Indian
  government/enterprise target market and MeitY empanelment) is deliberately deferred until
  after Decision Engine verification, per D-142's outstanding items.

## Storage & infrastructure

- **Document storage is local disk**, not cloud object storage (`STORAGE_ROOT`, MVP-scoped).
  Fine for a single-instance deployment; not fine for horizontal scaling or multi-instance
  durability.
- **No background job scheduler.** The freshness sweep (`POST /capabilities/check-freshness`)
  is on-demand only — no cron/queue infrastructure exists anywhere in this project.
- **Duplicate-execution guard is in-process, not distributed.** `Mission.status == RUNNING`
  is checked before starting; correct for a single-process deployment, not for multiple
  backend instances running concurrently.

## Data quality & validation

- **File upload validates extension + client-declared Content-Type only** — not real
  magic-byte content sniffing. A spoofed extension/Content-Type could bypass this check.
- **Requirement deduplication is deterministic exact-match only** (same type + normalized
  description). No semantic/fuzzy duplicate detection (two differently-worded restatements of
  the same requirement are not merged).
- **`GET /capabilities/{entity_id}` still returns an untyped response**, the same pattern
  `POST /capabilities/build` had before Milestone 6's fix. Discovered during that audit but
  explicitly not fixed, to keep that change incremental — see D-144.

## Testing

- **API-level integration test coverage is limited.** The only committed automated suite is
  the offline LLM provider layer (`tests/agents/test_llm_client.py`, 48 tests). There is no
  FastAPI `TestClient`-based integration suite exercising the routers, services, or database
  layer end-to-end. Every workflow has been verified manually/via Swagger during its
  milestone, not via a regression suite that runs on every change.

## Product & customer validation

- **No real pilot customer has used BidOps yet.** Every workflow (upload → analyze → decide →
  approve) has been verified with real documents by the people building it, not by an
  independent SME procurement team under real conditions. Onboarding experience, document
  taxonomy fit (see `BACKLOG.md` item 1), and the core value proposition itself are unvalidated
  against a real customer's actual tender.
- **No production deployment exists.** Everything above has been verified in development/
  sandbox environments only.

## Out of scope, not merely deferred

The following were considered and explicitly rejected as premature, not postponed pending
more engineering time: microservices, Kubernetes, CQRS, event buses, caching layers, plugin
architectures, additional LLM provider abstractions beyond the existing `LLMClient` protocol,
and rewriting the FastAPI/SQLAlchemy foundation. None of these are justified by any evidence
that exists today. Revisit only if real production usage or a real performance measurement
demonstrates a concrete bottleneck — not in the abstract.

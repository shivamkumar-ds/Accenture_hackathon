# BidOps — AI Architecture Principles (Governance Checklist)

Short-form companion to `CORE_ARCHITECTURE.md`. Use this to evaluate every future feature before it's designed, not just before it's built.

1. **AI is a scarce resource.** Never call an LLM where deterministic logic or already-known data would answer the question.
2. **Intelligence should compound.** Prefer AI operations that produce a reusable organizational asset over one-time inferences.
3. **Reason once, reuse while valid, recompute automatically when evidence changes.** Every reusable AI artifact needs a source, a version, a timestamp, and an invalidation trigger.
4. **Separate knowledge from reasoning.** Facts come from structured extraction and rules. The AI's budget is spent only on genuine judgment calls.
5. **Recommendation quality is sacred.** Optimize cost everywhere else first. Never trade match/compliance accuracy for savings.
6. **Product value should compound.** The moat is accumulated data (Capability Graph, Requirement/Evidence/Verdict history, outcomes) — not prompts, not model choice.
7. **Every feature must strengthen the moat.** If it doesn't improve quality, retention, knowledge, efficiency, explainability, trust, or differentiation, it's scope creep.
8. **Every AI conclusion must be traceable.** Every Verdict answers "why" with evidence, not chain-of-thought.

**The single working test for any new idea:** does it enrich the Requirement → Evidence → Evaluation → Verdict lifecycle? If not, it doesn't belong yet, regardless of how compelling it sounds on its own.

**Standing guardrails, reaffirmed across this discussion, not to be relitigated per-feature:**
- Never issue an AI-generated submit/don't-submit verdict. Diagnostic readiness only; the human decision stays human.
- Never invent a category the pipeline has no data to support (commercial, legal, competitive, strategic advice).
- Never present a confidence or readiness number that isn't one specific, named, computable statistic.
- External data sources are enhancements, never dependencies. Core product must work with all of them offline.
- No feature ships on assumption where verification is possible and hasn't been done (e.g. external API access, ToS, competitor claims).

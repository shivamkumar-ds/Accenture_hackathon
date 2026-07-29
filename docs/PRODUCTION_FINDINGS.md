# Production Findings Log

Started at the close of the architecture/engineering-governance phase (`ENGINEERING_DIRECTIVE.md` §"Post-Architecture Phase"). Purpose: give the next architecture discussion, if one happens, something to point at other than intuition. Per Principle 9 (`AI_ARCHITECTURE_PRINCIPLES.md`), a new design discussion opens only when a pattern repeats here — not on the first occurrence, not on a hunch.

Keep entries short. This is a findings log, not a report — a sentence or two per tender, plus the numbers.

## Validation Backlog

Process 10 real tenders across different industries/departments before drawing any conclusion. Government/PSU procurement varies enough by department (CPWD vs. a state PWD vs. a PSU tender, for instance) that fewer than this risks mistaking one department's drafting habits for a general pattern.

| # | Tender | Industry / Department | Processed | Notes |
|---|---|---|---|---|
| 1 | | | ☐ | |
| 2 | | | ☐ | |
| 3 | | | ☐ | |
| 4 | | | ☐ | |
| 5 | | | ☐ | |
| 6 | | | ☐ | |
| 7 | | | ☐ | |
| 8 | | | ☐ | |
| 9 | | | ☐ | |
| 10 | | | ☐ | |

## What to record per tender

Most of this is already captured automatically by Phase A instrumentation (`llm_call_events` table) and doesn't need manual tracking — pull it, don't re-measure it by hand:

- **Evaluation time** — `latency_ms` on `llm_call_events` where `purpose = 'decision_matching'`, summed per mission (or per-call, to see whether cost is concentrated in a few slow requirements or spread evenly).
- **Token cost** — `input_tokens`/`output_tokens` on the same rows, by `purpose` (`tender_requirement_extraction`, `capability_extraction`, `decision_matching`) — this is the breakdown that tells you which stage is actually expensive, not a guess.
- **Compliance verification frequency** — count of `POST /compliance/{id}/verify` calls per mission (visible via `AuditLog` rows with `agent = 'human_approval_layer'` and an event starting `"Compliance row"`), and how many of those were HIGH/CRITICAL blocking rows vs. advisory ones.
- **Manual overrides** — `AuditLog` rows for `record_decision` where the human's `BusinessDecision` disagreed with the AI's `RecommendationType` (e.g. AI said `conditional_go`, human recorded `rejected`) — this is the one number that most directly tells you whether the recommendation is actually trusted.

What needs manual judgment, not a query:

- **Recommendation quality** — did the executive summary and gap list actually reflect what a human reading the tender would conclude? Note specific misses, not just a rating.
- **False positives** — a requirement marked `met` that wasn't really satisfied by the cited evidence.
- **False negatives** — a requirement marked `not_met`/`review_required` that a human would call clearly satisfied.
- **Extraction quality** — did `tender_analyzer.py` find every real requirement, or miss/misclassify any? (Cross-check against a manual read of the tender document itself, not against the app's own output.)

## Findings Log

One entry per pattern noticed — not per tender. A single tender behaving oddly is a data point; three tenders behaving the same odd way is a finding.

```
### YYYY-MM-DD — <short title>

Observed in: <tender #s>
Pattern: <what recurred>
Evidence: <the numbers/examples, not just an impression>
Possible cause: <if known>
Action: <e.g. "watching," "logged as future work," "opening a design discussion because X">
```

(No entries yet — this section fills in as real tenders are processed.)

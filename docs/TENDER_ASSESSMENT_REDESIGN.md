# Tender Assessment — Information Architecture Redesign (Proposal)

Status: **Proposed — awaiting review.** Grows directly out of
`docs/TENDER_JOURNEY_DESIGN.md` (frozen) and
`docs/TENDER_JOURNEY_IMPLEMENTATION_PLAN.md` (implemented, all 7 phases
complete). This document proposes superseding *only* §3 of the design doc
— the mission page's information hierarchy — after using the finished
implementation end to end and concluding the hierarchy itself, not any
individual section's content, was the wrong shape. Nothing else in the
frozen design doc is reopened: the vocabulary rule (§1), the three-way
Requirements/Assessment/Decision History separation, the grounded backend
facts (§4), and everything marked explicitly deferred (§7) all stand.

No code, no component structure, no visual or styling change is proposed
here. This is information architecture only, per the discussion that
produced it — CSS, React, and card layout are all explicitly out of scope
until this is reviewed and approved.

## 1. The Problem, Restated Precisely

The implemented page contains correct information, presented in a
defensible order, and still doesn't work — because order isn't the same
thing as hierarchy, and hierarchy isn't the same thing as *cognition*.

Three distinct problems, easy to conflate, kept separate here:

- **Visual hierarchy** — does anything look bigger, bolder, or more
  prominent than anything else? Largely no: every section on the current
  page is the same card, the same border weight, the same width.
- **Sequential hierarchy** — is the order defensible? Yes — this is what
  the seven implemented phases actually fixed, and it was worth fixing.
- **Cognitive hierarchy** — does the page tell the reader what to think
  first, second, and only-if-they-ask? No. The page currently explains
  before it concludes. A procurement director reading top to bottom
  encounters "AI Recommendation," "Can we bid?", and "Should we bid?" as
  three separate assertions of the same underlying opinion before reaching
  a single reason, then reads the reasons twice (once as "what's blocking
  this bid," again as "what would change this recommendation") before
  reaching the one section that asks them to act.

The root technical cause: `recommendation_type` is a real, already-formed
opinion sitting in the data on day one (`go` / `conditional_go` / `review`
/ `no_go`). The page never lets it lead. It gets rendered as a label at
the top of a list of evidence, not spoken as a claim the rest of the page
defends. That's the actual gap between "AI analyzer" and "AI decision
support" — not a missing feature, a missing voice.

## 2. Product Principles Preserved

Unchanged from `TENDER_JOURNEY_DESIGN.md` §1, restated because this
document is judged against them:

- AI advises, humans decide. Nothing proposed here has the assessment
  perform, gate, or imply the Business Decision itself.
- Never fabricate certainty. Every proposed statement is checked in §5
  against what `RecommendationRead`, `GapAnalysisEntry`, and
  `ComplianceMatrixEntryRead` actually contain — nothing here requires a
  new metric the AI would have to invent.
- Requirements remains the AI's input, Decision History remains the
  human's outcome, and Tender Assessment (this document's proposed name —
  see §3) is the AI's reasoning in between. All three stay conceptually
  and structurally separate pages/sections, exactly as Phases 4 and 6
  built them. This document only redesigns the middle one.

One principle added by this discussion, not present in the original
design doc, promoted here to a first-class rule for anything built from
this point forward:

- **Every major section must answer exactly one business question.** If a
  section can't be summarized as the answer to one question a procurement
  director would actually ask, it doesn't earn independent existence — it
  either merges into a section that does, or becomes evidence behind one.

## 3. Direct Answers to the Questions This Discussion Raised

**Is "Tender Assessment" the right primary concept?** Yes, and it's a
better name than the current "AI Recommendation" page title for a precise
reason: a *recommendation* is directive — it tells someone what to do,
which edges toward the AI deciding. An *assessment* is diagnostic — it's
a read on the situation that a decision-maker then acts on. That maps
better onto "AI advises, human decides" than the word we shipped in Phase
1. This is a low-stakes, mechanical rename if it happens — same category
of change as Phase 1's "AI Decision" → "AI Recommendation" swap — not
raised here to reopen that work, just to answer the question directly.
The content rule matters far more than the label: whatever the section is
called, it must open with the verdict, not arrive at it.

**Should the page become a narrative instead of a collection of cards?**
Partially, and the distinction matters. The page should adopt narrative
*logic* — one throughline, each section answering the question the
previous one raises, a single voice making a claim and defending it. It
should **not** adopt narrative *form* — solid prose paragraphs replacing
scannable, labeled blocks. A procurement director with sixty seconds
scans, they don't read. The fix is sequencing and voice borrowed from
narrative, not literal paragraph text. Structured, scannable sections that
behave like a story — not a story.

**Which sections disappear, merge, or become evidence?** Full mapping in
§4. Short version: three sections that currently each assert some version
of "here's the verdict" (hero, "Can we bid?", "Should we bid?") become
one. Two sections that currently repeat the same gap list with different
phrasing ("What's Blocking," "What Would Change This Recommendation")
become one. The Compliance Matrix, the four-way confidence breakdown, and
the Compliance Summary tiles all move behind a single closed-by-default
disclosure. Nothing is deleted outright — everything that exists today
still exists, either merged or demoted, not lost.

**How should Review/Conditional differ from Go/No-Go?** This is the
sharpest correction this discussion produced. `recommendation_type` has
four values, not two, and `review` specifically means the AI is saying "I
don't have a confident answer — a human needs to look." If the opening
statement is written to sound equally decisive for all four values, the
page would be manufacturing confidence the AI doesn't have on exactly the
cases where honesty matters most. Go/No-Go should open with a plain
declarative claim ("We recommend not bidding"). Review/Conditional should
open with calibrated uncertainty in both the sentence and its framing
("This one is close — here's the split, your judgment decides it") —
different tone, not a weaker version of the same tone. `overall_confidence`
reinforces this either way: a `no_go` at high confidence and a `review` at
low confidence should not read like the same kind of statement wearing
different colors.

**Is there a better way to explain blockers than listing every failed
requirement?** Group by `requirement_type` (eligibility, technical,
certification, experience, evaluation_criteria, deadline, submission) —
this is a real, existing field on every `GapAnalysisEntry`, not a new
taxonomy. On top of that grouping, classify each category as
**Administrative** (certification, experience — things a company could
plausibly go acquire) or **Structural** (eligibility, scale — things that
don't change without becoming a different company). Flagged honestly in
§5: this classification is a fixed, human-authored mapping from the
existing seven-value enum, the same kind of judgment call already made
for `RECOMMENDATION_LABELS` and `STATUS_COPY` in the current codebase —
not a per-tender AI guess, and not new data. It should be reviewed and
signed off on once as a static mapping, not treated as self-evidently
correct.

**Can the AI communicate consequences without speculative claims?** Yes,
with one correction to how far that can go — see §5's worked example. The
short version: statements that restate what a mandatory-and-unmet
requirement already means in plain business language ("this would likely
be screened out before evaluation") are synthesis, not speculation.
Statements that claim knowledge of the tender issuer's own internal
process ("human review is unlikely") are not — BidOps has zero visibility
into that process and shouldn't imply it does.

**What should a procurement director understand in the first 30–60
seconds?** Answered as an actual time budget in §6, not a vague goal —
five seconds for the verdict and its color, fifteen for the reason, thirty
for whether it's fixable and what to do next. Everything past that is
something they chose to open.

## 4. Proposed Structure

Five tiers, each answering exactly one question, mapped against what
exists on the page today:

| Tier | Question | Absorbs (today) | Status |
|---|---|---|---|
| **The Assessment** | Should we bid? | Hero ("AI Recommendation"), "Can we bid?", "Should we bid?" | Merge into one block |
| **Why** | Why did we reach that? | "What's Blocking This Bid," gap reasons | Transform — grouped by category, consequence-first |
| **Can This Change** | Is this fixable? | "What Would Change This Recommendation?" | Transform — merged into Why per blocker, plus Administrative/Structural split |
| **What Should We Do** | What happens next? | Business Decision panel | Kept, but visually the destination — not another card of equal weight |
| **Evidence** | Where's the proof? | Compliance Summary tiles, Compliance Matrix, confidence breakdown | Collapse — one disclosure, closed by default |

**The Assessment** opens the page as a spoken claim, not a labeled data
point — "We recommend not bidding," not "Recommendation: No-Go." It holds
the eligibility gate (hard fact: N mandatory requirements unmet) and the
risk judgment (soft fact: overall risk level) as two distinct sentences
inside one block, preserving the real architectural distinction between
them (`blockingIssues` vs. `blockingRows` in the current implementation)
without needing two separate full-width sections to do it. Overall
confidence appears here twice — as a small number for scanning, and in
the wording of the sentence itself for reading. This tier alone should
satisfy the 5-second and 15-second marks in §6 for a clear-cut case.

**Why** groups every mandatory-and-not-met gap by its `requirement_type`
category, and each group carries its plain-language consequence, not just
its status — "Technical: 1 requirement unmet — this would likely be
screened out before evaluation," not a bare badge. This is where the two
currently-duplicated blocker sections become one.

**Can This Change** answers a genuinely different question than Why —
diagnosis versus prognosis — which is why it stays a distinct tier rather
than folding fully into Why. Administrative-versus-structural framing
lives here, restated per §3's honesty flag: a static category label, not
a computed score, and never phrased as a percentage or probability.

**What Should We Do** is unchanged in content from the current Business
Decision panel (condensed recap, Proceed/Rejected/Needs Changes, finality
copy) — its only change is weight. It should be the one place on the page
that reads as an instruction rather than exposition, which the first four
tiers exist to earn.

**Evidence** is the only tier that's a genuine behavior change, not just a
regroup: today the Compliance Summary tiles, the Compliance Matrix, and
the confidence breakdown are all visible by default, just positioned
lower. Here they're closed by default, one disclosure, opened on request
— this is where the Reviewer/Compliance Officer persona (already defined
in `TENDER_JOURNEY_DESIGN.md` §5) actually lives, not where a first-time
reader is expected to land.

**Explicitly untouched:** Requirements and Decision History remain
separate sections outside this five-tier structure, exactly as Phases 4
and 6 built them. Requirements is what the AI read before forming a view;
Decision History is what happened after a human acted on it. Neither
belongs inside "here's the assessment and why" — folding either in would
undo the three-way separation this whole redesign is built to protect,
not just a layout convenience.

## 5. Grounding Check — What's Real Data vs. What Would Be Invented

Every new piece of framing this document proposes is checked here against
the actual API contract (`frontend/src/api/types.ts`,
`RecommendationRead`, `GapAnalysisEntry`, `ComplianceMatrixEntryRead`) —
nothing above should be read as approved until it passes this check.

**Grounded, buildable from existing data, no backend change:**
- The merged Assessment block — pure presentation over
  `recommendation.recommendation_type`, `risk_level`, `overall_confidence`,
  and the existing `blockingIssues` count. No new fields.
- Blocker grouping by `requirement_type` — the field already exists on
  every `GapAnalysisEntry`.
- "This would likely be screened out before evaluation" and similar
  consequence framing for mandatory-and-not-met requirements — a
  restatement of what "mandatory, not met" already means, the same move
  already made for the forward-looking gap rewrite in Phase 3.
- Administrative/Structural classification — a static, human-authored
  mapping from the seven `RequirementType` values, computed once, not
  per-tender, not AI-generated. Needs product sign-off as a mapping (like
  `RECOMMENDATION_LABELS`), not treated as self-evidently correct.
- Review/Conditional calibrated framing — driven entirely by
  `recommendation_type` and `overall_confidence`, both already present.

**Explicitly rejected, would require inventing certainty:**
- Any numeric "difficulty to convert No-Go to Go" score. No ground truth
  exists to calibrate it against; an LLM-guessed percentage presented as
  fact is exactly the failure mode the "never fabricate certainty"
  principle exists to prevent. The Administrative/Structural split above
  is the grounded substitute — directionally useful, not falsely precise.
- Any claim about the tender issuer's internal review process (e.g. "human
  review is unlikely"). BidOps has no visibility into that process. Any
  consequence statement must describe what happens to *our submission*
  based on facts we hold, never speculate about the buyer's process.
- Any monetary or strategic "Business Impact" framing (deal size,
  strategic priority). No such field exists on `TenderRead` today. If this
  becomes real later, it needs a real data source — either captured at
  upload or entered separately — not implied by this redesign.

## 6. The 30–60 Second Contract

Not a vague aspiration — a literal budget the structure in §4 is designed
to hit:

- **0–5 seconds:** one word and one color. The Assessment tier's opening
  claim, nothing else required to be read.
- **5–15 seconds:** the dominant reason. Whether it's a hard eligibility
  failure or a risk judgment, stated in the same block, not requiring a
  scroll.
- **15–30 seconds:** whether it's fixable, and roughly how (Can This
  Change), plus what to do about it (What Should We Do) — both visible
  without opening the Evidence disclosure.
- **30+ seconds:** everything past this point is opened deliberately, not
  scrolled past involuntarily. If a reader never opens Evidence, they
  still walked away with a real, defensible understanding of the
  assessment — that's the test this structure is designed to pass.

## 7. What This Proposal Does Not Change

- The visual design system (`DESIGN_SYSTEM.md`) — no new colors,
  typography, or component styling proposed or implied.
- The Requirements section (Phase 4) and Decision History section (Phase
  6) — both stay exactly as implemented, outside this restructuring.
- The backend API surface — every grounded item in §5 is a presentation
  reorganization of data already returned by
  `GET /api/v1/evaluation/{missionId}`. No new endpoint, field, or schema
  change is required to build this.
- The vocabulary rule from `TENDER_JOURNEY_DESIGN.md` §1 (AI Recommendation
  / AI Analysis, never AI Decision) — fully preserved; the "Tender
  Assessment" rename proposed in §3 is compatible with it, not a
  replacement of it.

## 8. Open Items for Review

- Confirm or reject the "Tender Assessment" rename (§3) — cosmetic, but
  worth an explicit decision before it's built, same as any vocabulary
  change.
- Sign off on the Administrative/Structural mapping (§5) as a fixed,
  reviewable classification — this is the one piece of genuinely new
  interpretive content in this document and deserves scrutiny before
  implementation, not silent approval by omission.
- Confirm the Evidence tier should be a single unified disclosure (matrix
  + confidence + compliance summary together) rather than three
  independently-collapsible pieces — this document assumes "one show-your-
  work action" is stronger than three, but that's a judgment call worth
  stating explicitly rather than assuming.

## 9. Next Steps (Not Started)

If approved, this document freezes the same way `TENDER_JOURNEY_DESIGN.md`
did, and a new implementation plan gets written against it — phased,
reviewed, and approved the same way the seven Tender Journey phases were,
starting from the current frozen implementation rather than from scratch.
No implementation plan exists yet. No code has been written against this
document.

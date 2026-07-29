import type { GapAnalysisEntry } from "../api/types";

// "What would change this recommendation?" (docs/TENDER_JOURNEY_DESIGN.md
// §6, "cheap, buildable now" half only). Every not-met gap_analysis entry
// already has a `reason` -- LLM-generated prose, phrased retrospectively
// ("the provided record describes only one such project, which doesn't
// meet the minimum of three"). Rewriting that forward requires either
// sentence restructuring (an LLM concern, explicitly out of scope for this
// phase -- see the design doc's "Fix now" item) or a template. This is the
// template: a forward-looking prefix over the existing reason text,
// unchanged otherwise. No new data, no LLM call, no backend change.
//
// Deliberately conservative: entries without a `reason` fall back to a
// generic prompt rather than fabricating specifics that were never in the
// original analysis.
export function forwardLookingGap(entry: GapAnalysisEntry): string {
  if (!entry.reason) {
    return `To meet this requirement: address "${entry.description ?? "this requirement"}."`;
  }
  return `To meet this requirement: ${entry.reason}`;
}

import type { ComplianceMatrixEntryRead, GapAnalysisEntry, RiskLevel } from "../api/types";

// docs/TENDER_ASSESSMENT_REDESIGN.md §4/§5 -- "Top Priorities" ranking.
// Every ComplianceMatrixEntryRead already carries a real risk_level
// (critical/high/medium/low); joining it to its GapAnalysisEntry by the
// existing requirement_id key (same exact-ID join mergeRequirementContext
// already uses, not fuzzy matching) lets blockers be ordered by severity
// instead of left in whatever order the backend returned them. This reuses
// an existing signal for a new purpose -- it does not invent one.
//
// A blocker whose matrix row can't be found, or whose risk_level is null,
// falls back to "unranked" (sorted after every ranked blocker, order
// otherwise stable) rather than being assigned a fabricated severity --
// explicit rule from the redesign doc's grounding check (§5).
const SEVERITY_ORDER: Record<RiskLevel, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export interface RankedBlocker extends GapAnalysisEntry {
  riskLevel: RiskLevel | null;
}

// `blockers` is expected to already be the mandatory-and-not-met subset
// (i.e. what Evaluation.tsx computes as `blockingIssues`) -- this function
// only ranks, it doesn't decide what counts as a blocker.
export function rankBlockers(blockers: GapAnalysisEntry[], matrix: ComplianceMatrixEntryRead[]): RankedBlocker[] {
  const riskByRequirement = new Map<string, RiskLevel | null>();
  matrix.forEach((row) => riskByRequirement.set(row.requirement_id, row.risk_level));

  return blockers
    .map((g) => ({ ...g, riskLevel: riskByRequirement.get(g.requirement_id) ?? null }))
    .sort((a, b) => {
      const aRank = a.riskLevel ? SEVERITY_ORDER[a.riskLevel] : SEVERITY_ORDER.low + 1;
      const bRank = b.riskLevel ? SEVERITY_ORDER[b.riskLevel] : SEVERITY_ORDER.low + 1;
      return aRank - bRank;
    });
}

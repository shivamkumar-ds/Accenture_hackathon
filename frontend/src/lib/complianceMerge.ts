import type { ComplianceMatrixEntryRead, GapAnalysisEntry } from "../api/types";

// Every compliance-matrix row on its own only carries a requirement_id --
// no requirement text. gap_analysis entries (for every non-"met" row) DO
// carry the requirement's description + type + mandatory flag. Joining the
// two by requirement_id gives every row a real, human heading instead of
// the generic reasoning text or a raw evidence dump standing in for one.
// For the remaining "met" rows (which never appear in gap_analysis because
// there's nothing to flag), `notes` is already a well-written one-line
// justification, so it's the next best heading -- `supporting_evidence`
// (the raw matched record) is demoted to a collapsible detail either way.
// Shared between the Decision Engine page and the Reports page so both
// render/export the same requirement text instead of two divergent copies.
export function mergeRequirementContext(matrix: ComplianceMatrixEntryRead[], gaps: GapAnalysisEntry[]) {
  const byRequirement = new Map<string, GapAnalysisEntry>();
  gaps.forEach((g) => byRequirement.set(g.requirement_id, g));

  return matrix.map((entry) => {
    const gap = byRequirement.get(entry.requirement_id);
    return {
      ...entry,
      heading: gap?.description ?? entry.notes ?? "Requirement detail unavailable.",
      requirementType: gap?.requirement_type ?? null,
      mandatory: gap?.mandatory ?? null,
    };
  });
}

export type MergedComplianceEntry = ReturnType<typeof mergeRequirementContext>[number];

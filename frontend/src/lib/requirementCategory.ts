import type { RequirementType } from "../api/types";

// docs/TENDER_ASSESSMENT_REDESIGN.md §3/§5/§8 -- a static, human-authored,
// deterministic mapping from the existing seven-value RequirementType enum
// to a fixed "Administrative" / "Structural" classification. Same category
// of decision as RECOMMENDATION_LABELS (recommendationLabels.ts) and the
// Badge tone map (components/kit/Badge.tsx) -- a presentation-layer
// interpretation of a backend enum, not a per-tender AI guess and not new
// data. Binding conditions from the redesign doc's §8 sign-off: this lives
// in exactly one file, every mapping is documented inline, and the same
// RequirementType always produces the same classification -- never
// computed per-tender, never rendered as a score or percentage.
//
// Administrative -- things a company could plausibly go acquire without
// becoming a different company (certification, experience, procedural/
// submission fixes, evaluation-criteria positioning, and technical gaps
// that are commonly closed via hiring, subcontracting, or tooling).
// Structural -- things that don't change without becoming a different
// company, or that no amount of effort can move (eligibility rules the
// tender itself sets as fixed; hard deadlines, which are a fact of time,
// not a capability gap).
export type RequirementCategory = "administrative" | "structural";

export const REQUIREMENT_CATEGORY: Record<RequirementType, RequirementCategory> = {
  eligibility: "structural",
  deadline: "structural",
  certification: "administrative",
  experience: "administrative",
  evaluation_criteria: "administrative",
  submission: "administrative",
  // Technical gaps vary in practice, but the common case -- missing a
  // specific technology, tool, or technical capability -- is addressable
  // via hiring, subcontracting, or tooling investment rather than requiring
  // the company to become fundamentally different, so it's classified with
  // the administrative group. Documented here, not computed, per the
  // binding condition above.
  technical: "administrative",
};

export function requirementCategory(type: RequirementType): RequirementCategory {
  return REQUIREMENT_CATEGORY[type];
}

export const REQUIREMENT_CATEGORY_LABELS: Record<RequirementCategory, string> = {
  administrative: "Administrative",
  structural: "Structural",
};

import type { RequirementType } from "../api/types";
import type { RankedBlocker } from "./blockerPriority";

export interface BlockerGroup {
  type: RequirementType;
  label: string;
  items: RankedBlocker[];
  consequence: string;
}

function typeLabel(type: RequirementType): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// docs/TENDER_ASSESSMENT_REDESIGN.md §4/§5 -- a restatement of what
// "mandatory, not met" already means, the same move already made for the
// forward-looking gap rewrite (forwardLookingGap.ts, Phase 3 of the Tender
// Journey plan), not a per-type fabrication. Kept identical across every
// group deliberately: severity nuance lives in the ranking
// (blockerPriority.ts) and fixability nuance lives in the
// Administrative/Structural classification (requirementCategory.ts) --
// this sentence only needs to say what "not met, mandatory" means once.
const BLOCKING_CONSEQUENCE = "this would likely be screened out before evaluation";

// docs/TENDER_ASSESSMENT_REDESIGN.md §4 -- Why groups every mandatory-and-
// not-met gap by its requirement_type, and orders both the groups and the
// items within them by severity, not just by whatever order the backend
// returned them in. `ranked` is expected to already be severity-sorted
// (blockerPriority.ts's rankBlockers) -- this function only groups, and
// group order falls out naturally from first-appearance order in that
// already-sorted list, so the highest-severity group leads without a
// second sort here.
export function groupBlockersByType(ranked: RankedBlocker[]): BlockerGroup[] {
  const order: RequirementType[] = [];
  const byType = new Map<RequirementType, RankedBlocker[]>();

  ranked.forEach((b) => {
    if (!byType.has(b.requirement_type)) {
      order.push(b.requirement_type);
      byType.set(b.requirement_type, []);
    }
    byType.get(b.requirement_type)!.push(b);
  });

  return order.map((type) => {
    const items = byType.get(type)!;
    return {
      type,
      label: typeLabel(type),
      items,
      consequence: `${items.length} requirement${items.length === 1 ? "" : "s"} unmet — ${BLOCKING_CONSEQUENCE}`,
    };
  });
}

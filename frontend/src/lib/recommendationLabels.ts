import type { RecommendationType } from "../api/types";

// Frontend-only presentation layer over the backend's real enum values --
// the API keeps returning "go" / "no_go" / etc. unchanged, this just maps
// them to more executive-friendly language wherever a recommendation is
// displayed. No backend contract, schema, or business logic is touched.
export const RECOMMENDATION_LABELS: Record<RecommendationType, string> = {
  go: "Proceed",
  conditional_go: "Proceed with Conditions",
  review: "Review Required",
  no_go: "Do Not Proceed",
};

export function recommendationLabel(type: RecommendationType): string {
  return RECOMMENDATION_LABELS[type] ?? type;
}

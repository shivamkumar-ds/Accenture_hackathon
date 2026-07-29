import type { UserRole } from "../api/types";

// Static, human-authored copy explaining real, existing product behavior
// tied to each role -- not a new permission system, not invented
// functionality. Every sentence here describes something the product
// already does today:
// - executive/reviewer default to the Tender Assessment section when
//   opening a mission; auditor defaults to Decision History; bid_manager
//   and administrator have no fixed default (see roleDefaultSection() in
//   pages/Evaluation.tsx, which this text documents rather than
//   duplicates).
// - administrator is additionally the only role that can create users
//   today (POST /api/v1/users, backend-enforced) -- mentioned here even
//   though Team Management isn't part of this pass, because it's already
//   true of the role regardless of whether the UI for it exists yet.
// Same category of file as recommendationLabels.ts / requirementCategory.ts
// -- a single, documented, deterministic mapping over a backend enum.
export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  executive:
    "Opens directly to the Tender Assessment when viewing a mission -- the recommendation and business decision, not the raw requirements.",
  reviewer:
    "Opens directly to the Tender Assessment when viewing a mission, with full access to the Evidence tab for compliance verification.",
  auditor:
    "Opens directly to Decision History when viewing a mission -- the recorded audit trail of what happened and when.",
  bid_manager:
    "No fixed default view -- lands wherever a mission's current status makes most relevant (Requirements while still in progress, Tender Assessment once evaluated).",
  administrator:
    "No fixed default view, same as Bid Manager. Also the only role that can currently add new users to the organization.",
};

export function roleDescription(role: UserRole): string {
  return ROLE_DESCRIPTIONS[role];
}

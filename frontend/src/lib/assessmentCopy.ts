import type { RecommendationType } from "../api/types";
import type { RankedBlocker } from "./blockerPriority";

// docs/TENDER_ASSESSMENT_REDESIGN.md §3/§4 -- the Assessment tier opens
// with a spoken claim, not a labeled data point, and the claim's tone must
// be honest about how confident the AI actually is. Go/No-Go get a plain
// declarative sentence; Review/Conditional get calibrated-uncertainty
// framing -- a different tone, not a weaker version of the same one,
// because `review` specifically means the AI doesn't have a confident
// answer and a human needs to look.
export const ASSESSMENT_CLAIM: Record<RecommendationType, string> = {
  go: "We recommend proceeding with this bid.",
  no_go: "We recommend not bidding.",
  conditional_go: "This bid can proceed, with conditions attached.",
  review: "This one is close — here's the split, your judgment decides it.",
};

export function assessmentClaim(type: RecommendationType): string {
  return ASSESSMENT_CLAIM[type];
}

// The Assessment block's fourth line (§4, added in review): a single
// grounded business-consequence sentence, synthesized from whichever
// blocker ranks #1 by severity (blockerPriority.ts's rankBlockers),
// not written independently -- so the Assessment and Why tiers tell one
// continuous story instead of two separately-written summaries (§2's
// "no duplicate summaries" principle).
//
// Must be recommendation_type-aware, same discipline as the opening claim
// (§4): hard disqualification language is only accurate when a genuine
// mandatory-eligibility gap actually drove a No-Go. Every other case gets
// softer, risk-framed language -- never a uniform template applied
// regardless of what drove the verdict, and never a claim about the
// tender issuer's own internal review process (§5's explicit rejection).
export function assessmentConsequence(
  type: RecommendationType,
  topBlocker: RankedBlocker | undefined
): string | null {
  if (!topBlocker) return null;

  const isHardEligibilityNoGo = type === "no_go" && topBlocker.requirement_type === "eligibility";
  if (isHardEligibilityNoGo) {
    return "Submitting this tender today is likely to fail technical qualification due to mandatory eligibility gaps.";
  }

  return "Proceeding without addressing the flagged risk areas increases the likelihood of an unfavorable outcome.";
}

import type { MissionRead } from "../api/types";

// Real, human-meaningful tender identity: the user-entered tender name if
// they gave one at upload, else the actual uploaded file name (both
// resolved server-side onto MissionRead -- see its tender_name comment).
// mission_type is a fixed internal constant ("tender_evaluation" for every
// mission), never a tender name, so it's only the last-resort fallback for
// the rare case tender_name comes back null (e.g. an action-endpoint
// response that doesn't enrich it).
export function tenderDisplayName(m: Pick<MissionRead, "tender_name" | "mission_type">): string {
  return m.tender_name ?? m.mission_type;
}

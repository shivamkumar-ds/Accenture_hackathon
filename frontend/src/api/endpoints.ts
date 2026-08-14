import { apiClient } from "./client";
import type {
  ApprovalDecisionRequest,
  ApprovalHistoryResponse,
  CapabilityGraphResponse,
  ComplianceMatrixEntryRead,
  CompanyRead,
  ContactRequest,
  ContactResponse,
  DocumentRead,
  EvaluationResponse,
  GoogleLoginRequest,
  LoginRequest,
  MissionRead,
  RegisterRequest,
  TenderDocumentRead,
  TenderMetadataGuess,
  TenderUploadResponse,
  TenderWithRequirements,
  TokenResponse,
  UserRead,
  VerifyComplianceRequest,
} from "./types";

// --- auth ---

export const registerCompany = (payload: RegisterRequest) =>
  apiClient.post<TokenResponse>("/api/v1/auth/register", payload).then((r) => r.data);

export const login = (payload: LoginRequest) =>
  apiClient.post<TokenResponse>("/api/v1/auth/login", payload).then((r) => r.data);

export const getProfile = () => apiClient.get<UserRead>("/api/v1/auth/profile").then((r) => r.data);

// Login/link only -- fails cleanly (extractErrorMessage-surfaced) if no
// BidOps account exists yet for the Google account's email. Never creates
// a Company; see backend/app/services/auth_service.py::login_with_google
// for the full reasoning.
export const googleLogin = (payload: GoogleLoginRequest) =>
  apiClient.post<TokenResponse>("/api/v1/auth/google", payload).then((r) => r.data);

// --- contact ---

// Public landing page "Contact Us" form -- no auth token required (and
// none is sent even if a stale one happens to be in localStorage; the
// backend endpoint ignores it either way).
export const submitContactForm = (payload: ContactRequest) =>
  apiClient.post<ContactResponse>("/api/v1/contact", payload).then((r) => r.data);

// --- company ---

export const getCompany = (companyId: string) =>
  apiClient.get<CompanyRead>(`/api/v1/company/${companyId}`).then((r) => r.data);

// --- documents ---

export const listDocuments = () => apiClient.get<DocumentRead[]>("/api/v1/documents").then((r) => r.data);

export const uploadDocument = (file: File, documentType: string) => {
  const form = new FormData();
  form.append("document_type", documentType);
  form.append("file", file);
  return apiClient
    .post<DocumentRead>("/api/v1/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

// Soft-delete (removed_at) + real file removal server-side. Blocked with a
// 409 if an active tender or an active capability entity still references
// this document -- extractErrorMessage() surfaces that reason to the user.
export const deleteDocument = (documentId: string) =>
  apiClient.delete<DocumentRead>(`/api/v1/documents/${documentId}`).then((r) => r.data);

// --- capabilities ---

export const getCapabilityGraph = () =>
  apiClient.get<CapabilityGraphResponse>("/api/v1/capabilities").then((r) => r.data);

export const buildCapability = (documentId: string, entityType: string) =>
  apiClient
    .post("/api/v1/capabilities/build", { document_id: documentId, entity_type: entityType })
    .then((r) => r.data);

// Admin-only server-side (require_administrator) -- already-existing
// endpoint (M9 revalidation), just not previously called from the
// frontend. Soft-removes the entity and re-runs the Decision Engine for
// any mission whose current recommendation cited it.
export const deleteCapability = (entityId: string) =>
  apiClient.delete(`/api/v1/capabilities/${entityId}`).then((r) => r.data);

// --- tenders ---

export const uploadTender = (
  file: File,
  fields: { tender_name?: string; organization?: string; category?: string; closing_date?: string }
) => {
  const form = new FormData();
  form.append("file", file);
  if (fields.tender_name) form.append("tender_name", fields.tender_name);
  if (fields.organization) form.append("organization", fields.organization);
  if (fields.category) form.append("category", fields.category);
  if (fields.closing_date) form.append("closing_date", fields.closing_date);
  return apiClient
    .post<TenderUploadResponse>("/api/v1/tenders/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

// Best-effort, heuristic-only prefill read of a just-selected PDF -- never
// persisted server-side. Any/all fields can come back null.
export const extractTenderMetadata = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return apiClient
    .post<TenderMetadataGuess>("/api/v1/tenders/extract-metadata", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const getTender = (tenderId: string) =>
  apiClient.get<TenderWithRequirements>(`/api/v1/tenders/${tenderId}`).then((r) => r.data);

export const runAnalysis = (tenderId: string) =>
  apiClient
    .post<TenderWithRequirements>("/api/v1/analysis/run", { tender_id: tenderId })
    .then((r) => r.data);

// Attaches an additional source document (e.g. a technical bid detail
// spreadsheet, a BOQ) to an existing Tender -- multi-document Tender
// support. document_role is optional: the backend infers it from the
// filename ("boq"/"financial"/"price"/"commercial" -> financial, "tech"
// -> technical, else -> annexure) when omitted.
export const addTenderDocument = (tenderId: string, file: File, documentRole?: string) => {
  const form = new FormData();
  form.append("file", file);
  if (documentRole) form.append("document_role", documentRole);
  return apiClient
    .post<TenderDocumentRead>(`/api/v1/tenders/${tenderId}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

// --- evaluation / decision engine ---

export const runEvaluation = (missionId: string) =>
  apiClient.post<EvaluationResponse>("/api/v1/evaluation/run", { mission_id: missionId }).then((r) => r.data);

export const getEvaluation = (missionId: string) =>
  apiClient.get<EvaluationResponse>(`/api/v1/evaluation/${missionId}`).then((r) => r.data);

// --- missions ---

export const listMissions = () => apiClient.get<MissionRead[]>("/api/v1/missions").then((r) => r.data);

export const getMission = (missionId: string) =>
  apiClient.get<MissionRead>(`/api/v1/missions/${missionId}`).then((r) => r.data);

// Mission Orchestrator -- runs Tender Analysis (if not already done) and then
// Decision Intelligence evaluation, in one call, deciding what's needed from
// the mission/tender's own authoritative status. One action instead of two.
// `provider` selects which LLM engine runs this analysis -- only
// "openai" is accepted server-side right now (see ExecuteMissionRequest
// in the backend's mission schema); omitted falls back to the server's
// configured default, unchanged from before this parameter existed.
export const executeMission = (missionId: string, provider?: "openai") =>
  apiClient
    .post<MissionRead>(`/api/v1/missions/${missionId}/execute`, provider ? { provider } : undefined)
    .then((r) => r.data);

// Soft-delete (archive_mission -- flips status to "archived", never a real
// DELETE per the codebase's own Active/Archived/Deleted convention). This
// is what "delete tender" means in the UI: the mission/tender pair
// disappears from active views (Tender Workspace, Dashboard, Reports)
// but the row and its evaluation history survive.
export const archiveMission = (missionId: string) =>
  apiClient.delete<MissionRead>(`/api/v1/missions/${missionId}`).then((r) => r.data);

// Real, permanent deletion -- only succeeds server-side for an already-
// archived mission (mission_service.purge_mission's own ConflictError
// otherwise). Deliberately a separate call from archiveMission() above,
// not a flag on it: "hide it, recoverable" and "destroy it, irreversible"
// should never be one accidental parameter apart.
export const purgeMission = (missionId: string) =>
  apiClient.delete<void>(`/api/v1/missions/${missionId}/purge`).then(() => undefined);

// --- approval / Bid Decision ---
// "AI advises, human decides" -- this is the write path for the Bid
// Decision feature (docs/BID_DECISION_DESIGN.md). Backed by the existing
// Human Approval Layer (POST/GET /api/v1/approval), not a new endpoint --
// see that doc's §4 for why.

export const recordDecision = (payload: ApprovalDecisionRequest) =>
  apiClient.post<MissionRead>("/api/v1/approval", payload).then((r) => r.data);

export const getApprovalHistory = (missionId: string) =>
  apiClient.get<ApprovalHistoryResponse>(`/api/v1/approval/${missionId}`).then((r) => r.data);

// Atomic-layer override (CORE_ARCHITECTURE.md §7): a human verifying or
// rejecting one compliance row, independent of the mission-level Business
// Decision above. Returns the updated row so the caller can merge it back
// into local state without a full page refetch.
export const verifyComplianceRow = (complianceId: string, payload: VerifyComplianceRequest) =>
  apiClient
    .post<ComplianceMatrixEntryRead>(`/api/v1/compliance/${complianceId}/verify`, payload)
    .then((r) => r.data);

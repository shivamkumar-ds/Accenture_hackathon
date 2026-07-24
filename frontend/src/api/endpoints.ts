import { apiClient } from "./client";
import type {
  CapabilityGraphResponse,
  CompanyRead,
  DocumentRead,
  EvaluationResponse,
  LoginRequest,
  MissionRead,
  RegisterRequest,
  TenderUploadResponse,
  TenderWithRequirements,
  TokenResponse,
  UserRead,
} from "./types";

// --- auth ---

export const registerCompany = (payload: RegisterRequest) =>
  apiClient.post<TokenResponse>("/api/v1/auth/register", payload).then((r) => r.data);

export const login = (payload: LoginRequest) =>
  apiClient.post<TokenResponse>("/api/v1/auth/login", payload).then((r) => r.data);

export const getProfile = () => apiClient.get<UserRead>("/api/v1/auth/profile").then((r) => r.data);

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

// --- capabilities ---

export const getCapabilityGraph = () =>
  apiClient.get<CapabilityGraphResponse>("/api/v1/capabilities").then((r) => r.data);

export const buildCapability = (documentId: string, entityType: string) =>
  apiClient
    .post("/api/v1/capabilities/build", { document_id: documentId, entity_type: entityType })
    .then((r) => r.data);

// --- tenders ---

export const uploadTender = (
  file: File,
  fields: { tender_name?: string; organization?: string; closing_date?: string }
) => {
  const form = new FormData();
  form.append("file", file);
  if (fields.tender_name) form.append("tender_name", fields.tender_name);
  if (fields.organization) form.append("organization", fields.organization);
  if (fields.closing_date) form.append("closing_date", fields.closing_date);
  return apiClient
    .post<TenderUploadResponse>("/api/v1/tenders/upload", form, {
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

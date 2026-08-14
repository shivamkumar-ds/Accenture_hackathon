// Types mirror the real /openapi.json schema exactly (fetched and confirmed
// against the running backend, not guessed). Keep in sync if the backend
// contract changes -- per the MVP brief, that should be a rare, deliberate
// event, not a silent drift.

export type UserRole = "administrator" | "executive" | "bid_manager" | "reviewer" | "auditor";
export type UserStatus = "active" | "inactive";
export type DocumentProcessingStatus = "pending" | "processing" | "completed" | "failed";
export type RequirementType =
  | "eligibility"
  | "technical"
  | "certification"
  | "experience"
  | "evaluation_criteria"
  | "deadline"
  | "submission";
export type MatchStatus = "met" | "not_met" | "review_required" | "conditional";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RecommendationType = "go" | "conditional_go" | "review" | "no_go";
export type MissionStatus = "created" | "running" | "awaiting_approval" | "completed" | "archived";
// The human's Business Decision (Bid Decision feature) -- deliberately a
// separate vocabulary from RecommendationType (the AI's own output). "AI
// advises, human decides": these values are never the AI's to choose.
export type BusinessDecision = "proceed" | "rejected" | "needs_revision";
export type CapabilityEntityType = "certification" | "employee" | "project" | "equipment" | "financial_record";
export type VerificationStatus = "pending" | "verified" | "expired" | "review_required";

export interface UserRead {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface RegisterRequest {
  company_name: string;
  industry?: string | null;
  registration_number: string;
  country?: string | null;
  admin_name: string;
  admin_email: string;
  admin_password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// POST /api/v1/auth/google -- id_token is the credential Google Identity
// Services hands back to the frontend after the user picks an account;
// verified server-side (signature, expiry, audience), never trusted as-is.
// Login/link only: fails with a clean error if no BidOps account exists
// for the Google account's email -- this never creates a Company.
export interface GoogleLoginRequest {
  id_token: string;
}

// POST /api/v1/contact -- the public landing page's "Contact Us" form.
// Unauthenticated by design (a visitor submitting this has, by
// definition, no BidOps account yet). `website` is a honeypot: a hidden
// field a real visitor never sees or fills (see ContactSection.tsx) --
// always sent as an empty string by the real form.
export interface ContactRequest {
  full_name: string;
  work_email: string;
  company_name?: string | null;
  job_title?: string | null;
  phone?: string | null;
  subject: string;
  message: string;
  website?: string;
}

export interface ContactResponse {
  id: string;
  created_at: string;
}

export interface CompanyRead {
  id: string;
  name: string;
  industry?: string | null;
  registration_number: string;
  country?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentRead {
  id: string;
  company_id: string;
  uploaded_by: string;
  document_type: string;
  file_name: string;
  upload_time: string;
  version: number;
  processing_status: DocumentProcessingStatus;
}

export interface CapabilitySummary {
  total_entities: number;
  total_expired: number;
  total_stale: number;
  total_current: number;
  by_domain: Record<string, number>;
}

interface CapabilityCommon {
  id: string;
  company_id: string;
  confidence_score: number | null;
  source_document_id: string | null;
  verification_status: VerificationStatus;
  freshness_status: string;
  is_expired: boolean;
  is_stale: boolean;
  created_at: string;
}

export interface CertificationEntry extends CapabilityCommon {
  certification_name: string;
  issuing_authority: string | null;
  issue_date: string | null;
  expiry_date: string | null;
}

export interface EmployeeEntry extends CapabilityCommon {
  name: string;
  position: string | null;
  qualification: string | null;
  experience: string | null;
  skills: string[] | null;
}

export interface ProjectEntry extends CapabilityCommon {
  client: string | null;
  industry: string | null;
  contract_value: number | null;
  duration: string | null;
  completion_status: string | null;
  // Was already returned by the backend (ProjectRead.similarity_tags) but
  // missing from this type -- pre-existing drift, not a new field.
  similarity_tags: string[] | null;
}

export interface EquipmentEntry extends CapabilityCommon {
  equipment_name: string;
  category: string | null;
  quantity: number | null;
}

export interface FinancialRecordEntry extends CapabilityCommon {
  financial_year: number | null;
  revenue: number | null;
  net_worth: number | null;
  credit_rating: string | null;
}

export interface CapabilityGraphResponse {
  summary: CapabilitySummary;
  certifications: CertificationEntry[];
  employees: EmployeeEntry[];
  projects: ProjectEntry[];
  equipment: EquipmentEntry[];
  financial_records: FinancialRecordEntry[];
}

export interface RequirementRead {
  id: string;
  tender_id: string;
  requirement_type: RequirementType;
  description: string | null;
  mandatory: boolean;
  source_page: number | null;
  confidence: number | null;
}

export interface TenderRead {
  id: string;
  mission_id: string;
  tender_name: string | null;
  organization: string | null;
  category: string | null;
  closing_date: string | null;
  uploaded_document: string | null;
  processing_status: string | null;
}

export interface TenderWithRequirements {
  tender: TenderRead;
  requirements: RequirementRead[];
}

// Response for POST /tenders/extract-metadata -- heuristic-only (regex, no
// LLM call) best-effort read of a just-selected PDF, purely to prefill the
// New Tender form. Never persisted; any/all fields can come back null.
export interface TenderMetadataGuess {
  tender_name: string | null;
  organization: string | null;
  closing_date: string | null;
}

// The upload-tender endpoint's response is loosely typed in the OpenAPI spec
// (additionalProperties: true) rather than a named schema -- treat it
// defensively, but it should carry at least id + mission_id like TenderRead.
export interface TenderUploadResponse {
  tender_id: string;
  mission_id: string;
  tender_name?: string | null;
  organization?: string | null;
  closing_date?: string | null;
  [key: string]: unknown;
}

// Resolves ComplianceMatrixEntryRead.evidence_reference (an opaque
// CapabilityMapping id) into the actual company record + source document
// that grounds a recommendation -- the "Company Document" leg of the
// Decision Screen's signature evidence trail (DESIGN_SYSTEM.md §10).
export interface EvidenceSourceRead {
  entity_type: CapabilityEntityType;
  label: string;
  source_document_id: string | null;
  source_document_name: string | null;
}

// Excludes "pending" where the value is being set BY a human (that's the
// starting state, not a target one -- same rule the backend's
// VerifyComplianceRequest validator already enforces).
export type ComplianceMatrixVerificationStatus = "pending" | "verified_compliant" | "verified_non_compliant" | "escalated";
export type VerificationDecision = Exclude<ComplianceMatrixVerificationStatus, "pending">;

export interface ComplianceMatrixEntryRead {
  id: string;
  requirement_id: string;
  status: MatchStatus;
  supporting_evidence: string | null;
  notes: string | null;
  requires_verification: boolean;
  verification_reason: string | null;
  risk_level: RiskLevel | null;
  verification_status: ComplianceMatrixVerificationStatus;
  matching_confidence: number | null;
  evidence_reference: string | null;
  // "Source Clause" leg -- which tender document page this requirement came
  // from. "Company Document" leg -- which company record + upload backs it.
  source_page: number | null;
  evidence_source: EvidenceSourceRead | null;
  // Verification metadata (Compliance Verification UI). Never render
  // verified_by (a raw user id) directly -- verified_by_name is the
  // resolved display name, added specifically so the badge never has to
  // say "by you" for a mission another user opens later.
  verified_by: string | null;
  verified_by_name: string | null;
  verified_at: string | null;
}

// POST /api/v1/compliance/{id}/verify
export interface VerifyComplianceRequest {
  verification_status: VerificationDecision;
  note: string | null;
}

export interface GapAnalysisEntry {
  requirement_id: string;
  requirement_type: RequirementType;
  description: string | null;
  mandatory: boolean;
  status: MatchStatus;
  reason: string | null;
  source_page: number | null;
}

export interface RecommendationRead {
  id: string;
  mission_id: string;
  recommendation_type: RecommendationType;
  executive_summary: string | null;
  risk_level: RiskLevel | null;
  generated_at: string;
  document_confidence: number | null;
  entity_confidence: number | null;
  matching_confidence: number | null;
  recommendation_confidence: number | null;
  overall_confidence: number | null;
  snapshot_id: string | null;
}

export interface EvaluationResponse {
  recommendation: RecommendationRead;
  compliance_matrix: ComplianceMatrixEntryRead[];
  gap_analysis: GapAnalysisEntry[];
}

export interface MissionRead {
  id: string;
  company_id: string;
  user_id: string;
  mission_type: string;
  status: MissionStatus;
  created_at: string;
  completed_at: string | null;
  recommendation_id: string | null;
  capability_snapshot_id: string | null;
  actual_outcome: string | null;
  outcome_notes: string | null;
  // Real tender identity, resolved server-side from the linked Tender row
  // (user-entered tender name, falling back to the uploaded file name) --
  // mission_type is always the fixed constant "tender_evaluation" and was
  // never a tender name. Only populated by GET /missions and
  // GET /missions/:id; null on other mission action responses.
  tender_id: string | null;
  tender_name: string | null;
}

// --- Bid Decision (Human Approval Layer -- POST/GET /api/v1/approval) ---

export interface ApprovalDecisionRequest {
  mission_id: string;
  decision: BusinessDecision;
  // Required server-side when decision === "rejected"; optional otherwise.
  reason: string | null;
}

export interface DecisionEventRead {
  user_id: string | null;
  event: string;
  result: string | null;
  timestamp: string;
  // Additive (TENDER_JOURNEY_IMPLEMENTATION_PLAN.md Phase 6) -- resolved
  // server-side from user_id, same pattern as
  // ComplianceMatrixEntryRead.verified_by_name.
  user_name: string | null;
}

export interface ApprovalHistoryResponse {
  mission: MissionRead;
  recommendation: RecommendationRead;
  compliance_matrix: ComplianceMatrixEntryRead[];
  decision_events: DecisionEventRead[];
}

export interface ApiErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiValidationError {
  detail: ApiErrorDetail[];
}

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
// Architecture debate Phase 1 -- what KIND of unresolved requirement this
// is (orthogonal to RequirementType, which is what SECTION of the tender
// it came from). Nullable on older/legacy requirements extracted before
// this field existed; always present on anything extracted going forward.
export type RequirementNature =
  | "capability_claim"
  | "submission_gating"
  | "procedural"
  | "future_contractual_commitment";
// Architecture debate Phase 2/5 -- derived evaluation states computed
// server-side by decision_engine.compute_qualification()/
// compute_bid_readiness(); never independently recomputed on the frontend.
export type QualificationStatus = "pass" | "conditional" | "fail";
export type ReadinessStatus = "ready" | "action_required" | "blocked";
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

// PATCH /api/v1/company/{id} -- Administrator-only. Deliberately excludes
// registration_number: that's the tenant's legal/uniqueness identity, not
// an ordinary editable detail (see backend app/schemas/company.py's
// CompanyUpdate docstring). All fields optional -- only send what
// actually changed; omitted fields are left untouched server-side.
export interface CompanyUpdate {
  name?: string;
  industry?: string | null;
  country?: string | null;
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
  // Which attached document this requirement came from, and where in it
  // (e.g. "Sheet: Sheet1" for a spreadsheet-sourced requirement) --
  // multi-document Tender support. May be null for requirements extracted
  // before this feature existed.
  source_document_id: string | null;
  source_location: string | null;
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

// One document attached to a Tender -- the main PDF or any additional
// technical/financial/annexure document (multi-document Tender support).
export type TenderDocumentRole = "main" | "technical" | "financial" | "annexure" | string;

export interface TenderDocumentRead {
  id: string;
  file_name: string;
  document_role: TenderDocumentRole | null;
  upload_time: string;
}

export interface TenderWithRequirements {
  tender: TenderRead;
  requirements: RequirementRead[];
  documents: TenderDocumentRead[];
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
  // Architecture debate Phase 5 additions -- populated from
  // decision_engine.reconstruct_match_result() (see backend
  // app/schemas/decision.py's GapAnalysisEntry docstring). Both nullable/
  // defaulted-empty since older requirements predate requirement_nature
  // (Phase 1) and most requirements resolve to zero unsupported domains.
  requirement_nature: RequirementNature | null;
  unsupported_domains: CapabilityEntityType[];
  // Bid-readiness confirmation feature -- whether a human has confirmed
  // this item (a SUBMISSION_GATING/FUTURE_CONTRACTUAL_COMMITMENT gap) is
  // actually prepared. The item stays in its bucket either way (never
  // dropped) -- confirmed just changes how it's displayed and whether it
  // still counts as "unresolved" in remediation_summary.bid_readiness.
  confirmed: boolean;
  confirmed_at: string | null;
  // Qualification override feature -- whether an administrator has
  // explicitly overridden this item (a mandatory CAPABILITY_CLAIM
  // qualification gap) despite no real capability evidence existing for
  // it yet. Unlike `confirmed` (an already-true fact), `overridden`
  // represents an explicit, audited risk acceptance -- render it
  // visually distinct from "requirement met," never absorbed into it.
  overridden: boolean;
  overridden_by: string | null;
  overridden_by_name: string | null;
  overridden_at: string | null;
  override_note: string | null;
}

// Architecture debate Phase 5 -- the single deterministic backend
// representation of "what does this evaluation actually require, and
// why" (app/schemas/decision.py's RemediationSummary). The frontend/PDF
// render these buckets directly; they do not independently reclassify
// gap_analysis entries into qualification/readiness/coverage/review
// groups -- that decision is made once, server-side, by
// decision_engine.classify_remediation().
export interface RemediationSummary {
  qualification: QualificationStatus;
  qualification_gaps: GapAnalysisEntry[];

  bid_readiness: ReadinessStatus;
  blocked_items: GapAnalysisEntry[];
  action_required_items: GapAnalysisEntry[];

  coverage_gaps: GapAnalysisEntry[];

  human_review_items: GapAnalysisEntry[];

  // Architecture debate Phase 6 (REVIEW-explainability gap) -- non-
  // mandatory CAPABILITY_CLAIM requirements with a definitive NOT_MET
  // verdict. Not a qualification risk (qualification only ever looks at
  // mandatory items) and not ambiguous (NOT_MET is definitive, nothing
  // for a human to adjudicate) -- but the one item shape that can push
  // `recommendation.recommendation_type` to "review" (via the backend's
  // settings.max_optional_review_items threshold) while contributing to
  // no other bucket here. Render this directly; never recompute the
  // threshold or re-derive this set from gap_analysis/compliance_matrix
  // client-side -- see decision_engine.classify_remediation()'s
  // docstring for the exhaustive backend-side proof that this is the
  // only such item shape.
  optional_capability_gaps: GapAnalysisEntry[];
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
  // Required, not optional -- the deployed backend contract (Phase 5)
  // guarantees this is always populated on every EvaluationResponse.
  // Do not add a fallback/degraded path for its absence; see the Phase 6
  // inspection report's discussion of backward compatibility.
  remediation_summary: RemediationSummary;
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

// --- Bid-readiness confirmation ---
// POST/DELETE /api/v1/missions/{mission_id}/requirements/{requirement_id}/confirm

export interface BidReadinessConfirmationRead {
  id: string;
  requirement_id: string;
  confirmed_by: string;
  confirmed_at: string;
  note: string | null;
}

// --- Qualification override ---
// POST/DELETE /api/v1/missions/{mission_id}/requirements/{requirement_id}/override
// Distinct from bid-readiness confirmation -- see GapAnalysisEntry.overridden's
// own comment. A real, audited administrator risk-acceptance, not a
// confirmation of an already-true fact; note is REQUIRED at creation time.
export interface QualificationOverrideRead {
  id: string;
  requirement_id: string;
  overridden_by: string;
  overridden_at: string;
  note: string | null;
}

// --- Manual capability creation -- POST /api/v1/capabilities/manual ---
// No document required, admin-gated. Supports all five entity types
// (unlike POST /capabilities/build, which only supports the three with a
// document-extraction agent). `fields` is intentionally loose (matches
// the backend's ManualCapabilityCreateRequest.fields dict[str, Any]) --
// per-entity-type validation happens server-side.
export interface ManualCapabilityCreateRequest {
  entity_type: CapabilityEntityType;
  fields: Record<string, unknown>;
}

// --- Capability field update -- PATCH /api/v1/capabilities/{id} ---
// Pre-existing M9 endpoint (revalidation_service.handle_capability_update),
// generic across all five entity types via capability_service.PATCHABLE_FIELDS
// -- only just extended to cover Equipment/FinancialRecord. `fields` mirrors
// the same loose dict[str, Any] shape as manual creation; unknown/unpatchable
// field names 422 server-side.
export interface CapabilityUpdateRequest {
  fields: Record<string, unknown>;
}

export interface RevalidationResult {
  entity_id: string;
  changed_fields: string[];
  affected_missions: string[];
  new_recommendations: string[];
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

// --- Portfolio (GET /api/v1/portfolio) ---
// Mirrors backend/app/schemas/portfolio.py exactly. Purely a read model
// over data the Decision Engine / Evaluation response already produce --
// no new persisted concept, no frontend-side recomputation of any of it
// (bucket, insight, active-mission definition all come from the backend
// as-is; see Portfolio.tsx's own comment).

export interface OpportunitySummary {
  mission_id: string;
  tender_name: string | null;
  // LIVE-recomputed value (same one GET /evaluation/{mission_id} returns,
  // override-aware) -- never derived client-side.
  recommendation_type: RecommendationType;
  overall_confidence: number | null;
}

export interface NotYetAnalyzedMission {
  mission_id: string;
  tender_name: string | null;
  status: MissionStatus;
}

export interface UnableToLoadMission {
  mission_id: string;
  tender_name: string | null;
}

export interface PortfolioInsight {
  what: string;
  why: string;
  now_what: string;
  affected_requirement_types: RequirementType[];
  affected_mission_ids: string[];
}

// Second, deliberately minimal Portfolio insight -- HOW MANY active
// opportunities carry any mandatory qualification gap (vs. the flagship
// PortfolioInsight's WHAT single requirement-type is most common). Counts
// a mission even if the gap has since been overridden -- an override is
// bid-specific risk acceptance, not proof the underlying gap disappeared.
export interface QualificationRiskExposure {
  what: string;
}

export interface PortfolioResponse {
  prioritize: OpportunitySummary[];
  review: OpportunitySummary[];
  deprioritize: OpportunitySummary[];
  not_yet_analyzed: NotYetAnalyzedMission[];
  unable_to_load: UnableToLoadMission[];
  // null only when there are zero analyzed missions with at least one
  // qualification gap between them.
  insight: PortfolioInsight | null;
  // null only when there are zero analyzed active missions; otherwise
  // always present, including the honest "0 of M" case.
  qualification_risk_exposure: QualificationRiskExposure | null;
  analyzed_count: number;
  active_count: number;
}

import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getApprovalHistory,
  getCompany,
  getEvaluation,
  getMission,
  getTender,
  recordDecision,
  runAnalysis,
  runEvaluation,
  verifyComplianceRow,
} from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { recommendationLabel } from "../lib/recommendationLabels";
import { mergeRequirementContext, type MergedComplianceEntry } from "../lib/complianceMerge";
import { tenderDisplayName } from "../lib/tenderName";
import { forwardLookingGap } from "../lib/forwardLookingGap";
import { rankBlockers } from "../lib/blockerPriority";
import { groupBlockersByType } from "../lib/blockerGroups";
import { assessmentClaim, assessmentConsequence } from "../lib/assessmentCopy";
import { requirementCategory, REQUIREMENT_CATEGORY_LABELS } from "../lib/requirementCategory";
import type {
  BusinessDecision,
  ComplianceMatrixEntryRead,
  DecisionEventRead,
  EvaluationResponse,
  MatchStatus,
  MissionRead,
  RecommendationRead,
  RequirementType,
  TenderWithRequirements,
  UserRole,
  VerificationDecision,
} from "../api/types";
import {
  AIProcessing,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfidenceBar,
  ConfidenceRing,
  EmptyState,
  FilterChip,
  SearchInput,
  Skeleton,
  Textarea,
} from "../components/kit";
import {
  AlertOctagon,
  ArrowRight,
  Check,
  ChevronDown,
  Download,
  FileSearch,
  History,
  Lightbulb,
  RefreshCw,
  ShieldCheck,
  ShieldQuestion,
  TrendingUp,
  X,
} from "lucide-react";
import { cn } from "../lib/cn";

// The three real target values a human can verify a compliance row to --
// "pending" is the starting state, never a target one (same rule the
// backend's VerifyComplianceRequest validator already enforces).
const VERIFY_OPTIONS: { value: VerificationDecision; label: string }[] = [
  { value: "verified_compliant", label: "Verified Compliant" },
  { value: "verified_non_compliant", label: "Verified Non-Compliant" },
  { value: "escalated", label: "Escalated" },
];

const DECISION_STAGES = [
  "Loading capability library…",
  "Matching requirements against evidence…",
  "Scoring compliance and risk…",
  "Drafting executive recommendation…",
];

// Absorbed from the now-deleted TenderDetail.tsx (Phase 4).
const ANALYSIS_STAGES = [
  "Parsing tender document…",
  "Identifying clauses and obligations…",
  "Classifying requirement types…",
  "Scoring confidence per requirement…",
];

// Display order for the grouped matrix -- the things that need a human's
// attention lead, "met" (i.e. nothing to do) trails and starts collapsed.
const STATUS_ORDER: MatchStatus[] = ["not_met", "review_required", "conditional", "met"];

const STATUS_COPY: Record<MatchStatus, string> = {
  not_met: "Not Met",
  review_required: "Review Required",
  conditional: "Conditional",
  met: "Met",
};

function statusCount(matrix: ComplianceMatrixEntryRead[], status: MatchStatus) {
  return matrix.filter((m) => m.status === status).length;
}

type MergedEntry = MergedComplianceEntry;

// Requirements / AI Recommendation / Decision History -- collapses the
// former TenderDetail.tsx + Evaluation.tsx route split into sections of one
// page (docs/TENDER_JOURNEY_DESIGN.md §5, TENDER_JOURNEY_IMPLEMENTATION_PLAN.md
// Phases 4 and 6). Business Decision itself is not a fourth section here --
// see docs/TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md's Phase 4 entry for why
// (already integrated into the AI Recommendation scroll by Phase 2).
type MissionSection = "requirements" | "recommendation" | "history";

// Second-level navigation inside the "recommendation" (Tender Assessment)
// section only -- docs/TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md's
// navigation-hierarchy iteration. This solves a different problem than
// MissionSection above: MissionSection separates the AI's input
// (Requirements), the AI's reasoning (Tender Assessment), and the human's
// audit trail (Decision History) -- three genuinely different data
// sources, left untouched here per the explicit "do not merge" constraint.
// AssessmentTab instead splits *one* section's own content into a
// workspace (Overview / Analysis / Decision / Evidence) purely so the
// user navigates instead of scrolling through one long report -- no new
// data source, no new fetch, same `data`/`recommendation` object as
// before this iteration.
type AssessmentTab = "overview" | "analysis" | "decision" | "evidence";

const ASSESSMENT_TABS: { value: AssessmentTab; label: string }[] = [
  { value: "overview", label: "Overview" },
  { value: "analysis", label: "Analysis" },
  { value: "decision", label: "Decision" },
  { value: "evidence", label: "Evidence" },
];

// Role-based default section (TENDER_JOURNEY_IMPLEMENTATION_PLAN.md Phase
// 7, docs/TENDER_JOURNEY_DESIGN.md §5's persona table). mission.status
// (see refresh() below) determines what's actually possible to show; this
// determines where a given role lands among what's available -- it never
// overrides the "nothing to show yet" created/running case.
//
// Reviewer defaults to "recommendation," not a dedicated "Supporting
// Evidence" section, because no such section exists: the Compliance Matrix
// lives inside the AI Recommendation section (Phase 2 demoted it below the
// Business Decision panel, not into its own tab) -- same reasoning already
// recorded in docs/TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md's Phase 4 entry
// for why Business Decision itself isn't a separate section either.
//
// Administrator is the design doc's own explicitly-flagged open question
// ("where Administrator fits this table... worth confirming before
// implementation"). Resolved here per the implementation plan's proposed
// default -- same as Bid Manager, no fixed default -- rather than left
// unimplemented; flagging the choice here rather than picking silently.
function roleDefaultSection(role: UserRole | undefined): MissionSection | null {
  switch (role) {
    case "executive":
      return "recommendation";
    case "reviewer":
      return "recommendation";
    case "auditor":
      return "history";
    case "bid_manager":
    case "administrator":
    default:
      return null;
  }
}

export default function Evaluation() {
  const { missionId } = useParams<{ missionId: string }>();
  const { notify } = useToast();
  const { user } = useAuth();
  const [mission, setMission] = useState<MissionRead | null>(null);
  const [tenderData, setTenderData] = useState<TenderWithRequirements | null>(null);
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [missionNotFound, setMissionNotFound] = useState(false);
  const [section, setSection] = useState<MissionSection>("requirements");
  // Second-level nav within the recommendation section -- local component
  // state, same pattern as `section` above. No routing change and no URL
  // state: nothing in this iteration asked for a shareable deep link to a
  // specific tab, and local state matches the existing `section` switcher
  // exactly, so this stays consistent rather than introducing a second
  // state-management approach for one sub-nav. Starts on "overview" --
  // every fresh visit lands on the executive-summary tab.
  const [assessmentTab, setAssessmentTab] = useState<AssessmentTab>("overview");
  const [analyzing, setAnalyzing] = useState(false);
  const [running, setRunning] = useState(false);
  const [requirementTypeFilter, setRequirementTypeFilter] = useState<RequirementType | "all">("all");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<MatchStatus | "all">("all");
  const [expanded, setExpanded] = useState<Record<MatchStatus, boolean>>({
    not_met: true,
    review_required: true,
    conditional: false,
    met: false,
  });
  // Analysis tab -- blocker groups (Why) default collapsed, keyed by
  // RequirementType. Missing key === collapsed; explicit `true` === open.
  // Kept separate from `expanded` above (that one's the Evidence tab's
  // Compliance Matrix status groups -- a different list, different
  // question, deliberately not the same state).
  const [expandedBlockerGroups, setExpandedBlockerGroups] = useState<Record<string, boolean>>({});
  // For the PDF report's company name field only (Phase 5) -- same
  // best-effort, non-blocking fetch Reports.tsx used before this button
  // moved here.
  const [companyName, setCompanyName] = useState("");
  const [generatingPdf, setGeneratingPdf] = useState(false);
  // Decision History (Phase 6) -- getApprovalHistory() also returns
  // mission/recommendation/compliance_matrix, but this page already has
  // all of that from its own fetches; only decision_events is new data.
  const [decisionEvents, setDecisionEvents] = useState<DecisionEventRead[]>([]);

  useEffect(() => {
    if (!user?.company_id) return;
    getCompany(user.company_id)
      .then((c) => setCompanyName(c.name))
      .catch(() => undefined);
  }, [user?.company_id]);

  const refresh = async () => {
    if (!missionId) return;
    setLoading(true);
    setMissionNotFound(false);
    try {
      const missionResult = await getMission(missionId);
      setMission(missionResult);
      // Section default logic: mission.status (Phase 4) determines what's
      // actually possible to show -- a created/running mission has nothing
      // to recommend, verify, or audit yet, so it always lands on
      // Requirements regardless of role. Once past that, role (Phase 7)
      // determines where a given role lands among what's now available.
      const statusDefault: MissionSection =
        missionResult.status === "created" || missionResult.status === "running" ? "requirements" : "recommendation";
      setSection(statusDefault === "requirements" ? "requirements" : roleDefaultSection(user?.role) ?? statusDefault);

      // Requirements data -- independent of whether the Decision Engine has
      // run. mission.tender_id should always be present once a tender
      // upload succeeds, but this is guarded defensively rather than
      // assumed.
      if (missionResult.tender_id) {
        try {
          setTenderData(await getTender(missionResult.tender_id));
        } catch (err) {
          notify("error", extractErrorMessage(err));
        }
      }

      // AI Recommendation data -- legitimately absent (404) until the
      // Decision Engine has run at least once. That's an expected product
      // state, not a page-level error, so it's handled separately from the
      // mission fetch above instead of failing the whole page.
      try {
        setData(await getEvaluation(missionId));
      } catch {
        setData(null);
      }

      // Decision History data -- same "legitimately absent" reasoning as
      // the evaluation fetch above: get_approval_history() 404s until a
      // recommendation exists (approval_service.get_approval_history()),
      // which is exactly the condition the evaluation fetch above already
      // handles. Independent try/catch rather than nesting inside that one
      // so a failure here never masks a successful evaluation fetch.
      try {
        setDecisionEvents((await getApprovalHistory(missionId)).decision_events);
      } catch {
        setDecisionEvents([]);
      }
    } catch {
      setMissionNotFound(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId]);

  // Absorbed from the now-deleted TenderDetail.tsx (Phase 4) -- extracts
  // requirements from the tender document. Stays on the Requirements
  // section; does not switch sections on its own.
  const handleAnalyze = async () => {
    if (!mission?.tender_id) return;
    setAnalyzing(true);
    try {
      const result = await runAnalysis(mission.tender_id);
      setTenderData(result);
      notify("success", `${result.requirements.length} requirements extracted.`);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRun = async () => {
    if (!missionId) return;
    setRunning(true);
    try {
      const result = await runEvaluation(missionId);
      setData(result);
      // Re-running moves the mission to awaiting_approval (or resets a
      // prior decision's completed status) -- refetch so the Business
      // Decision panel below reflects the mission's real current state.
      setMission(await getMission(missionId));
      setSection("recommendation");
      setAssessmentTab("overview");
      notify("success", "Decision Engine evaluation complete.");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  const merged = useMemo(
    () => (data ? mergeRequirementContext(data.compliance_matrix, data.gap_analysis) : []),
    [data]
  );

  // Phase 5: folds Reports.tsx's former "Download PDF Report" action into
  // the mission page it was always describing -- same generateEvaluationPdf
  // call, same merged data, same meta shape, just invoked from here instead
  // (docs/TENDER_JOURNEY_IMPLEMENTATION_PLAN.md Phase 5). lib/pdfReport.ts
  // itself is untouched.
  const handleDownloadPdf = async () => {
    if (!data || !mission) return;
    setGeneratingPdf(true);
    try {
      const { generateEvaluationPdf } = await import("../lib/pdfReport");
      generateEvaluationPdf(data, merged, {
        companyName,
        missionType: tenderDisplayName(mission),
        missionId: mission.id,
      });
    } catch {
      notify("error", "Couldn't generate the PDF report.");
    } finally {
      setGeneratingPdf(false);
    }
  };

  const blockingIssues = useMemo(
    () => (data?.gap_analysis ?? []).filter((g) => g.mandatory && g.status === "not_met"),
    [data]
  );

  // docs/TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md Phase 1/2 -- severity-
  // ranked view of blockingIssues (Why's "Top Priorities" ordering, and the
  // Assessment tier's #1-ranked blocker for its consequence sentence). Kept
  // as its own memo rather than folded into blockingIssues above so the
  // "what counts as a blocker" logic and "how they're ordered" logic stay
  // independently readable.
  const rankedBlockers = useMemo(
    () => rankBlockers(blockingIssues, data?.compliance_matrix ?? []),
    [blockingIssues, data]
  );

  // docs/TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md Phase 3 -- Why's grouped,
  // severity-ranked view of the same blockers. Derived from rankedBlockers
  // (already severity-sorted) so group order and in-group order both fall
  // out of that single sort, not a second one.
  const whyGroups = useMemo(() => groupBlockersByType(rankedBlockers), [rankedBlockers]);

  // UI-only readiness indicator, mirroring (not duplicating) the backend's
  // approval_service.get_blocking_rows() rule -- the backend remains the
  // sole enforcement (a 409 on Save is still possible, e.g. a race with
  // another user), this is guidance computed entirely from fields already
  // on the wire so a blocking row is visible before Save is even clicked.
  const blockingRows = useMemo(
    () =>
      (data?.compliance_matrix ?? []).filter(
        (row) =>
          row.requires_verification &&
          (row.risk_level === "high" || row.risk_level === "critical") &&
          row.verification_status === "pending"
      ),
    [data]
  );

  const handleRowVerified = (updated: ComplianceMatrixEntryRead) => {
    setData((prev) =>
      prev
        ? { ...prev, compliance_matrix: prev.compliance_matrix.map((row) => (row.id === updated.id ? updated : row)) }
        : prev
    );
  };

  const filtered = useMemo(() => {
    return merged.filter((c) => {
      const matchesStatus = statusFilter === "all" || c.status === statusFilter;
      const matchesQuery =
        !query ||
        c.heading.toLowerCase().includes(query.toLowerCase()) ||
        c.supporting_evidence?.toLowerCase().includes(query.toLowerCase());
      return matchesStatus && matchesQuery;
    });
  }, [merged, statusFilter, query]);

  const grouped = useMemo(() => {
    const groups: Record<MatchStatus, MergedEntry[]> = { not_met: [], review_required: [], conditional: [], met: [] };
    filtered.forEach((entry) => groups[entry.status].push(entry));
    return groups;
  }, [filtered]);

  // Requirements section data -- absorbed from the now-deleted
  // TenderDetail.tsx (Phase 4). Memoized (not a plain `?? []` fallback) so
  // its identity is stable across renders -- otherwise the `?? []` creates
  // a new empty array every render, which would make the useMemo hooks
  // below that depend on it re-run every time for no reason.
  const requirements = useMemo(() => tenderData?.requirements ?? [], [tenderData]);
  const requirementTypes = useMemo(
    () => Array.from(new Set(requirements.map((r) => r.requirement_type))),
    [requirements]
  );
  const filteredRequirements = useMemo(
    () =>
      requirementTypeFilter === "all"
        ? requirements
        : requirements.filter((r) => r.requirement_type === requirementTypeFilter),
    [requirements, requirementTypeFilter]
  );

  if (running) {
    return (
      <Card>
        <CardBody>
          <AIProcessing stages={DECISION_STAGES} />
        </CardBody>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (missionNotFound || !mission) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Mission</h1>
        </div>
        <Card>
          <CardBody>
            <EmptyState
              icon={TrendingUp}
              title="Mission not found"
              description="This mission may have been deleted, or the link is incorrect."
            />
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{tenderDisplayName(mission)}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {tenderData?.tender.organization ?? "No organization specified"}
          </p>
        </div>
        {section === "recommendation" && data && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              icon={<Download size={14} />}
              loading={generatingPdf}
              onClick={handleDownloadPdf}
            >
              Download PDF Report
            </Button>
            <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} onClick={handleRun}>
              Re-run
            </Button>
          </div>
        )}
      </div>

      {/* Requirements / AI Recommendation / Decision History section
          switcher -- collapses the former TenderDetail.tsx +
          Evaluation.tsx route split into one page (docs/
          TENDER_JOURNEY_DESIGN.md §5; TenderDetail deleted in Phase 4).
          Reusing FilterChip as the switcher rather than introducing a new
          tab component -- no equivalent exists in the kit yet and this
          phase's scope is a page merge, not a new UI primitive. */}
      <div className="flex gap-2">
        <FilterChip label="Requirements" active={section === "requirements"} onClick={() => setSection("requirements")} />
        <FilterChip
          label="Tender Assessment"
          active={section === "recommendation"}
          onClick={() => setSection("recommendation")}
        />
        <FilterChip label="Decision History" active={section === "history"} onClick={() => setSection("history")} />
      </div>

      {section === "requirements" && (
        <div className="space-y-6">
          <Card>
            <CardBody>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Organization</p>
                  <p className="font-medium">{tenderData?.tender.organization ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Closing Date</p>
                  <p className="font-medium">{tenderData?.tender.closing_date ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Status</p>
                  {tenderData?.tender.processing_status ? <Badge value={tenderData.tender.processing_status} /> : "—"}
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Requirements</p>
                  <p className="font-medium tabular-nums">{requirements.length}</p>
                </div>
              </div>
            </CardBody>
          </Card>

          {analyzing ? (
            <Card>
              <CardBody>
                <AIProcessing stages={ANALYSIS_STAGES} />
              </CardBody>
            </Card>
          ) : requirements.length === 0 ? (
            <Card>
              <CardBody>
                <EmptyState
                  icon={FileSearch}
                  title="Ready to analyze"
                  description="Run the Tender Analyzer to extract requirements from this document."
                  action={<Button onClick={handleAnalyze}>Run Tender Analyzer</Button>}
                />
              </CardBody>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader
                  title="Extracted Requirements"
                  description={`${filteredRequirements.length} of ${requirements.length} shown`}
                  action={
                    <Button variant="outline" size="sm" onClick={handleAnalyze}>
                      Re-run Analyzer
                    </Button>
                  }
                />
                <CardBody>
                  <div className="flex flex-wrap gap-2 mb-4">
                    <FilterChip
                      label="All"
                      active={requirementTypeFilter === "all"}
                      onClick={() => setRequirementTypeFilter("all")}
                    />
                    {requirementTypes.map((t) => (
                      <FilterChip
                        key={t}
                        label={t.replace(/_/g, " ")}
                        active={requirementTypeFilter === t}
                        onClick={() => setRequirementTypeFilter(t)}
                      />
                    ))}
                  </div>
                  <ul className="divide-y divide-border -mx-6">
                    {filteredRequirements.map((r) => (
                      <li key={r.id} className="px-6 py-3 text-sm">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <span className="leading-relaxed min-w-0">{r.description}</span>
                          <div className="flex items-center gap-2 shrink-0">
                            {r.mandatory && <Badge value="mandatory" />}
                            <Badge value={r.requirement_type} />
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Page {r.source_page ?? "—"} · confidence{" "}
                          {r.confidence != null ? `${Math.round(r.confidence * 100)}%` : "—"}
                        </p>
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>

              <Card className="border-primary/30 bg-primary/[0.03]">
                <CardBody>
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="text-sm font-semibold">Ready for Decision Engine</h2>
                      <p className="text-sm text-muted-foreground mt-1">
                        Match these {requirements.length} requirements against your capability library and generate a
                        recommendation.
                      </p>
                    </div>
                    <Button onClick={handleRun} size="lg" icon={<ArrowRight size={15} />}>
                      Run Decision Engine
                    </Button>
                  </div>
                </CardBody>
              </Card>
            </>
          )}
        </div>
      )}

      {section === "recommendation" &&
        (!data ? (
          <Card>
            <CardBody>
              <EmptyState
                icon={TrendingUp}
                title="This mission hasn't been evaluated yet"
                description={
                  requirements.length === 0
                    ? "Extract requirements in the Requirements section first, then run the Decision Engine."
                    : "Run the Decision Engine to match requirements against your capability library and generate a recommendation."
                }
                action={requirements.length > 0 ? <Button onClick={handleRun}>Run Evaluation</Button> : undefined}
              />
            </CardBody>
          </Card>
        ) : (
          // IIFE so `data` (already narrowed non-null by the ternary above)
          // can be destructured once for this whole block, same as the
          // pre-Phase-4 top-level destructure -- avoids threading a large
          // prop list through a separate component for what is still just
          // one page's JSX.
          (() => {
            const { recommendation, compliance_matrix } = data;
            const accentBar =
              recommendation.recommendation_type === "go"
                ? "bg-success"
                : recommendation.recommendation_type === "no_go"
                ? "bg-danger"
                : "bg-warning";
            return (
              <div className="space-y-6">
                {/* Second-level navigation -- docs/
                    TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md's navigation-
                    hierarchy iteration. The information hierarchy below
                    (Overview -> Analysis -> Decision -> Evidence) is
                    unchanged from the frozen redesign's five tiers; what
                    changed is that the reader now navigates between them
                    instead of scrolling through all of them at once.
                    Deliberately a different visual language (underlined
                    tabs, smaller text) than the pill-style FilterChip
                    switcher above (Requirements / Tender Assessment /
                    Decision History) -- two levels of navigation need two
                    distinct visual weights, or this just becomes six flat
                    tabs and recreates the same problem one layer down. */}
                <div className="flex items-center gap-1 border-b border-border">
                  {ASSESSMENT_TABS.map((t) => (
                    <button
                      key={t.value}
                      type="button"
                      onClick={() => setAssessmentTab(t.value)}
                      className={cn(
                        "px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                        assessmentTab === t.value
                          ? "border-primary text-foreground"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>

                {/* Overview -- the merged Assessment block (Phase 2),
                    unchanged in content: opens with a spoken claim, holds
                    the eligibility gate and risk judgment as two distinct
                    sentences, closes with the grounded consequence line
                    synthesized from the #1-ranked blocker. Designed to fit
                    above the fold on a normal laptop with nothing else on
                    the tab competing for space -- this alone should
                    satisfy the redesign doc's 5-15 second budget for a
                    clear-cut case. Never "AI Decision" -- vocabulary rule
                    unchanged (docs/TENDER_JOURNEY_DESIGN.md §1);
                    "Decision" is reserved for the human action in the
                    Decision tab. */}
                {assessmentTab === "overview" && (
                  <div className="space-y-4">
                    <div className="relative rounded-xl border bg-surface p-6 sm:p-8 shadow-hero overflow-hidden">
                      <div className={cn("absolute left-0 top-0 bottom-0 w-1.5", accentBar)} />
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">The Assessment</span>
                      <div className="flex flex-col md:flex-row items-start md:items-center gap-8 mt-3">
                        <div className="flex-1 space-y-3 min-w-0 order-2 md:order-1">
                          <p className="font-display font-semibold text-3xl md:text-4xl tracking-tight leading-tight">
                            {assessmentClaim(recommendation.recommendation_type)}
                          </p>
                          {recommendation.executive_summary && (
                            <p className="text-sm leading-relaxed text-foreground/80 max-w-2xl">{recommendation.executive_summary}</p>
                          )}
                        </div>
                        <div className="order-1 md:order-2 flex flex-col items-center gap-1.5 shrink-0">
                          <ConfidenceRing value={recommendation.overall_confidence} size={104} />
                          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Overall Confidence</span>
                        </div>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-5 mt-8 pt-6 border-t border-border">
                        <div className="flex items-start gap-3">
                          {blockingIssues.length > 0 ? (
                            <AlertOctagon size={20} className="text-danger shrink-0 mt-0.5" />
                          ) : (
                            <ShieldCheck size={20} className="text-success shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Can we bid?</p>
                            <p className="text-sm font-semibold tracking-tight">
                              {blockingIssues.length > 0
                                ? `No — ${blockingIssues.length} mandatory requirement${blockingIssues.length === 1 ? "" : "s"} not met`
                                : "Yes — every mandatory requirement is met"}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <ShieldQuestion size={20} className="text-muted-foreground shrink-0 mt-0.5" />
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Should we bid?</p>
                            {recommendation.risk_level ? (
                              <p className="text-sm text-foreground/80 leading-relaxed">
                                Overall risk assessed as{" "}
                                <span className="font-medium text-foreground">{recommendation.risk_level}</span>, based on{" "}
                                {blockingIssues.length > 0
                                  ? `${blockingIssues.length} unresolved mandatory requirement(s).`
                                  : "no unresolved mandatory requirements."}
                              </p>
                            ) : (
                              <p className="text-sm text-muted-foreground">No risk level was returned for this evaluation.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      {assessmentConsequence(recommendation.recommendation_type, rankedBlockers[0]) && (
                        <p className="text-sm leading-relaxed text-foreground/90 mt-6 pt-6 border-t border-border">
                          {assessmentConsequence(recommendation.recommendation_type, rankedBlockers[0])}
                        </p>
                      )}
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => setAssessmentTab("analysis")}
                        className="inline-flex items-center gap-1 text-sm font-medium text-brand-accent hover:underline"
                      >
                        See Analysis
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Analysis -- Why + What Would It Take together (Phases 3
                    and 4), unchanged in content and still two distinct
                    cards (diagnosis vs. prognosis stays a real distinction
                    per the redesign doc), just no longer sharing the page
                    with Overview/Decision/Evidence. Blocker groups within
                    Why now default collapsed -- "Technical -- 7 blockers"
                    with a count, not nine visible rows -- expanding on
                    click reveals the individual blockers. Reduces what's
                    on screen without hiding anything; the group's
                    consequence line stays visible either way so collapsing
                    a group doesn't cost the reader its meaning. */}
                {assessmentTab === "analysis" && (
                  <div className="space-y-6">
                    {whyGroups.length > 0 ? (
                      <Card className="border-danger/30">
                        <CardHeader
                          title={
                            <span className="flex items-center gap-2">
                              <AlertOctagon size={15} className="text-danger" />
                              Why
                            </span>
                          }
                          description={`${blockingIssues.length} mandatory requirement(s) not met, top priorities first`}
                        />
                        <CardBody className="!py-2 divide-y divide-border -mx-6">
                          {whyGroups.map((group) => {
                            const isOpen = expandedBlockerGroups[group.type] ?? false;
                            return (
                              <div key={group.type} className="px-6 py-3">
                                <button
                                  type="button"
                                  onClick={() =>
                                    setExpandedBlockerGroups((prev) => ({ ...prev, [group.type]: !isOpen }))
                                  }
                                  className="w-full flex items-center justify-between gap-3 text-left"
                                >
                                  <span className="flex items-center gap-2">
                                    <span className="text-sm font-semibold">{group.label}</span>
                                    <Badge value={group.type} />
                                  </span>
                                  <span className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                                    {group.items.length} blocker{group.items.length === 1 ? "" : "s"}
                                    <ChevronDown size={14} className={cn("transition-transform", isOpen && "rotate-180")} />
                                  </span>
                                </button>
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{group.consequence}</p>
                                {isOpen && (
                                  <ul className="divide-y divide-border mt-2 -mx-6 border-t border-border">
                                    {group.items.map((g) => (
                                      <li key={g.requirement_id} className="px-6 py-3 text-sm">
                                        <div className="flex items-start justify-between gap-3">
                                          <span className="font-medium leading-relaxed">{g.description}</span>
                                          {g.riskLevel && <Badge value={g.riskLevel} withIcon />}
                                        </div>
                                        {g.reason && (
                                          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{g.reason}</p>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            );
                          })}
                        </CardBody>
                      </Card>
                    ) : (
                      <Card>
                        <CardBody>
                          <p className="text-sm text-muted-foreground">
                            No mandatory requirements are unmet -- there's nothing blocking this bid to analyze.
                          </p>
                        </CardBody>
                      </Card>
                    )}

                    {rankedBlockers.length > 0 && (
                      <Card className="border-primary/20">
                        <CardHeader
                          title={
                            <span className="flex items-center gap-2">
                              <Lightbulb size={15} className="text-primary" />
                              What Would It Take
                            </span>
                          }
                          description="What it would take to clear each mandatory blocker"
                        />
                        <CardBody className="!py-2">
                          <ul className="divide-y divide-border -mx-6">
                            {rankedBlockers.map((g) => (
                              <li key={g.requirement_id} className="px-6 py-3 text-sm">
                                <div className="flex items-start justify-between gap-3">
                                  <p className="font-medium leading-relaxed">{g.description}</p>
                                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide shrink-0">
                                    {REQUIREMENT_CATEGORY_LABELS[requirementCategory(g.requirement_type)]}
                                  </span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{forwardLookingGap(g)}</p>
                              </li>
                            ))}
                          </ul>
                        </CardBody>
                      </Card>
                    )}
                  </div>
                )}

                {/* Decision -- the Business Decision panel (Phase 5),
                    unchanged in content, now a real destination tab rather
                    than the fourth card in a scroll. Decision History
                    stays a separate top-level section, not merged --
                    per the redesign doc's explicit constraint and this
                    iteration's own -- the link below is a navigation
                    shortcut into that existing section, not a duplicate of
                    its content. */}
                {assessmentTab === "decision" && (
                  <div className="space-y-4">
                    {mission && (
                      <BusinessDecisionPanel
                        mission={mission}
                        blockingRowCount={blockingRows.length}
                        mandatoryBlockerCount={blockingIssues.length}
                        recommendation={recommendation}
                        onDecisionRecorded={setMission}
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => setSection("history")}
                      className="inline-flex items-center gap-1 text-sm font-medium text-brand-accent hover:underline"
                    >
                      <History size={14} />
                      View Decision History
                      <ArrowRight size={14} />
                    </button>
                  </div>
                )}

                {/* Evidence -- docs/TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md's
                    navigation-hierarchy iteration removes the closed-by-
                    default <details> Phase 6 introduced: navigating to this
                    tab is now itself the disclosure gesture, so wrapping
                    the content in a second, redundant collapse would just
                    add a click on top of a click. Content is otherwise
                    unchanged -- confidence breakdown, Compliance Summary,
                    and the Compliance Matrix, still structurally separate
                    from Decision History (row-level verification
                    provenance here vs. the mission-level Business Decision
                    audit trail there). */}
                {assessmentTab === "evidence" && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                      <ConfidenceBar label="Document Confidence" value={recommendation.document_confidence} />
                      <ConfidenceBar label="Entity Confidence" value={recommendation.entity_confidence} />
                      <ConfidenceBar label="Matching Confidence" value={recommendation.matching_confidence} />
                      <ConfidenceBar label="Recommendation Confidence" value={recommendation.recommendation_confidence} />
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Compliance Summary</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <StatusStat label="Met" status="met" count={statusCount(compliance_matrix, "met")} />
                        <StatusStat label="Not Met" status="not_met" count={statusCount(compliance_matrix, "not_met")} />
                        <StatusStat label="Review Required" status="review_required" count={statusCount(compliance_matrix, "review_required")} />
                        <StatusStat label="Conditional" status="conditional" count={statusCount(compliance_matrix, "conditional")} />
                      </div>
                    </div>

                    {/* Compliance matrix -- grouped by status instead of one
                        long flat scroll, requirement text leads every row,
                        raw matched evidence is tucked behind a "View
                        evidence" disclosure instead of printed in full for
                        every single row. Unchanged since Phase 6 except its
                        container. */}
                    <Card>
                      <CardHeader
                        title="Compliance Matrix"
                        description={`${filtered.length} of ${compliance_matrix.length} requirements · supporting evidence per row`}
                        action={<SearchInput value={query} onChange={setQuery} placeholder="Search requirements…" />}
                      />
                      <CardBody>
                        <div className="flex flex-wrap gap-2 mb-2">
                          <FilterChip label="All" active={statusFilter === "all"} onClick={() => setStatusFilter("all")} />
                          {STATUS_ORDER.map((s) => (
                            <FilterChip key={s} label={STATUS_COPY[s]} active={statusFilter === s} onClick={() => setStatusFilter(s)} />
                          ))}
                        </div>

                        {statusFilter === "all" ? (
                          <div className="-mx-6 divide-y divide-border">
                            {STATUS_ORDER.filter((s) => grouped[s].length > 0).map((status) => (
                              <div key={status}>
                                <button
                                  onClick={() => setExpanded((prev) => ({ ...prev, [status]: !prev[status] }))}
                                  className="w-full flex items-center justify-between gap-3 px-6 py-3 text-sm font-medium hover:bg-surface-hover transition-colors"
                                >
                                  <span className="flex items-center gap-2">
                                    <Badge value={status} withIcon />
                                    <span className="text-muted-foreground font-normal">{grouped[status].length} requirement(s)</span>
                                  </span>
                                  <ChevronDown size={15} className={cn("text-muted-foreground transition-transform", expanded[status] && "rotate-180")} />
                                </button>
                                {expanded[status] && (
                                  <ul className="divide-y divide-border bg-muted/30">
                                    {grouped[status].map((entry) => (
                                      <MatrixRow
                                        key={entry.id}
                                        entry={entry}
                                        missionStatus={mission?.status ?? null}
                                        onVerified={handleRowVerified}
                                      />
                                    ))}
                                  </ul>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <ul className="divide-y divide-border -mx-6">
                            {filtered.map((entry) => (
                              <MatrixRow
                                key={entry.id}
                                entry={entry}
                                missionStatus={mission?.status ?? null}
                                onVerified={handleRowVerified}
                              />
                            ))}
                          </ul>
                        )}
                      </CardBody>
                    </Card>
                  </div>
                )}
              </div>
            );
          })()
        ))}

      {/* Decision History -- read-only audit trail, backed by the
          previously-unused GET /approval/{mission_id} (Phase 6). Renders
          every recorded event chronologically (compliance verifications and
          the final Business Decision alike -- both are logged through the
          same Human Approval Layer, approval_service.py's _log()), each
          attributed to a real user name where resolvable. */}
      {section === "history" && (
        <Card>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <History size={15} className="text-muted-foreground" />
                Decision History
              </span>
            }
            description={
              decisionEvents.length
                ? `${decisionEvents.length} event${decisionEvents.length === 1 ? "" : "s"}`
                : undefined
            }
          />
          <CardBody>
            {decisionEvents.length === 0 ? (
              <EmptyState
                icon={History}
                title="No decision history yet"
                description="Compliance verifications and the recorded Business Decision will appear here once this mission has a recommendation."
              />
            ) : (
              <ul className="divide-y divide-border -mx-6">
                {decisionEvents.map((e, i) => (
                  <li key={`${e.timestamp}-${i}`} className="px-6 py-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-medium leading-relaxed">{e.event}</p>
                      <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                        {new Date(e.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{e.user_name ?? "Unknown user"}</p>
                    {e.result && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{e.result}</p>}
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function MatrixRow({
  entry,
  missionStatus,
  onVerified,
}: {
  entry: MergedEntry;
  missionStatus: MissionRead["status"] | null;
  onVerified: (updated: ComplianceMatrixEntryRead) => void;
}) {
  // The signature evidence trail (DESIGN_SYSTEM.md §10): Recommendation
  // (the row itself) -> Evidence -> Source Clause -> Company Document.
  // Each step only renders if the backend actually resolved it -- no
  // placeholder text stands in for a step that isn't real, per "evidence
  // First" (PRODUCT_CONSTITUTION.md §7): every claim here is traceable.
  const hasTrail = Boolean(entry.supporting_evidence || entry.source_page != null || entry.evidence_source);

  // Verification state is local to the row, not lifted to the page --
  // deliberately mirrors the independent, uncoupled <details> pattern the
  // evidence trail above already uses. Nothing coordinates which row's
  // form is open because nothing needs to; multiple rows can be mid-verify
  // at once with zero shared state.
  const { notify } = useToast();
  const [isVerifying, setIsVerifying] = useState(false);
  const [draftStatus, setDraftStatus] = useState<VerificationDecision>("verified_compliant");
  const [draftNote, setDraftNote] = useState("");
  const [saving, setSaving] = useState(false);

  // Gated on mission lifecycle, not just requires_verification -- once a
  // mission is no longer awaiting_approval, the backend already rejects
  // further verification (approval_service.py's AWAITING_APPROVAL check),
  // so showing an action that can only 409 would be misleading.
  const canVerify = entry.requires_verification && missionStatus === "awaiting_approval";
  const isVerified = entry.verification_status !== "pending";

  const openForm = () => {
    setDraftStatus("verified_compliant");
    setDraftNote("");
    setIsVerifying(true);
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      const updated = await verifyComplianceRow(entry.id, {
        verification_status: draftStatus,
        note: draftNote.trim() || null,
      });
      onVerified(updated);
      notify("success", "Compliance row verified.");
      setIsVerifying(false);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <li className="px-6 py-3.5 text-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium leading-relaxed pr-2">{entry.heading}</p>
        <div className="flex items-center gap-2 shrink-0">
          {entry.mandatory && <Badge value="mandatory" />}
          {entry.risk_level && <Badge value={entry.risk_level} />}
          {entry.matching_confidence != null && (
            <span className="text-xs text-muted-foreground tabular-nums">{Math.round(entry.matching_confidence * 100)}% match</span>
          )}
        </div>
      </div>
      {hasTrail && (
        <details className="mt-1.5 group">
          <summary className="text-xs text-brand-accent cursor-pointer select-none list-none inline-flex items-center gap-1 hover:underline">
            <ChevronDown size={12} className="transition-transform group-open:rotate-180" />
            View evidence trail
          </summary>
          <div className="mt-1.5 border-l-2 border-border pl-3 space-y-1.5">
            {entry.supporting_evidence && (
              <p className="text-xs text-muted-foreground leading-relaxed">
                <span className="font-medium text-foreground/70">Evidence — </span>
                {entry.supporting_evidence}
              </p>
            )}
            {entry.source_page != null && (
              <p className="text-xs text-muted-foreground leading-relaxed">
                <span className="font-medium text-foreground/70">Source clause — </span>
                Tender document, page {entry.source_page}
              </p>
            )}
            {entry.evidence_source && (
              <p className="text-xs text-muted-foreground leading-relaxed">
                <span className="font-medium text-foreground/70">Company record — </span>
                {entry.evidence_source.label}
                {entry.evidence_source.source_document_name && ` (${entry.evidence_source.source_document_name})`}
              </p>
            )}
          </div>
        </details>
      )}
      {entry.notes && entry.notes !== entry.heading && (
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{entry.notes}</p>
      )}

      {canVerify && (
        <div className="mt-2">
          {isVerified ? (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge value={entry.verification_status} withIcon />
              {entry.verified_by_name && (
                <span className="text-muted-foreground">
                  Verified by {entry.verified_by_name}
                  {entry.verified_at && ` · ${new Date(entry.verified_at).toLocaleString()}`}
                </span>
              )}
              <button type="button" onClick={openForm} className="text-brand-accent hover:underline">
                Change verification
              </button>
            </div>
          ) : !isVerifying ? (
            <button
              type="button"
              onClick={openForm}
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-accent hover:underline"
            >
              <ShieldCheck size={12} />
              Verify
            </button>
          ) : (
            <div className="space-y-2 border-l-2 border-border pl-3">
              <div className="flex flex-wrap gap-2">
                {VERIFY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setDraftStatus(opt.value)}
                    className={cn(
                      "rounded-md border px-2.5 py-1 text-xs font-medium transition-colors",
                      draftStatus === opt.value
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-surface hover:bg-surface-hover"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <Textarea
                placeholder="Note (optional)"
                value={draftNote}
                onChange={(e) => setDraftNote(e.target.value)}
                rows={2}
              />
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setIsVerifying(false)} disabled={saving}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleConfirm} loading={saving}>
                  Confirm
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

const DECISION_OPTIONS: { value: BusinessDecision; label: string; icon: typeof Check }[] = [
  { value: "proceed", label: "Proceed", icon: Check },
  { value: "rejected", label: "Rejected", icon: X },
  // Labeled "Needs Changes" in the UI per BID_DECISION_DESIGN.md §3 --
  // "revision" reads as if the tender itself needs rework, when really
  // it's the company's own eligibility that needs work. The underlying
  // value stays needs_revision; this is a display-only relabel.
  { value: "needs_revision", label: "Needs Changes", icon: RefreshCw },
];

function BusinessDecisionPanel({
  mission,
  blockingRowCount,
  mandatoryBlockerCount,
  recommendation,
  onDecisionRecorded,
}: {
  mission: MissionRead;
  blockingRowCount: number;
  // Mandatory-and-not-met count (the "Can we bid?" / "What's Blocking
  // This Bid" figure) -- distinct from blockingRowCount, which gates on
  // unverified HIGH/CRITICAL compliance rows. Used only for the recap
  // below, not for any gating logic (unchanged from before this reorder).
  mandatoryBlockerCount: number;
  recommendation: RecommendationRead;
  onDecisionRecorded: (mission: MissionRead) => void;
}) {
  const { notify } = useToast();
  const [selected, setSelected] = useState<BusinessDecision | null>(null);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const alreadyDecided = mission.status === "completed";

  const handleSave = async () => {
    if (!selected) return;
    if (selected === "rejected" && !reason.trim()) {
      notify("error", "A reason is required when rejecting a bid.");
      return;
    }
    setSaving(true);
    try {
      const updated = await recordDecision({
        mission_id: mission.id,
        decision: selected,
        reason: reason.trim() || null,
      });
      onDecisionRecorded(updated);
      notify("success", "Business decision saved.");
      setSelected(null);
      setReason("");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  // docs/TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md Phase 5 -- "What Should
  // We Do" is unchanged in content from the panel that existed before this
  // phase (redesign doc §4: same recap, same Proceed/Rejected/Needs
  // Changes options, same finality copy); only its visual weight changes,
  // so it reads as the page's destination rather than another card of
  // equal weight to the four tiers above it. Reuses the existing
  // border-primary/30 + bg-primary/[0.03] treatment already established
  // for "the destination" card elsewhere on this page (the "Ready for
  // Decision Engine" card in the Requirements section) -- no new color or
  // component added to the design system, per §7's explicit constraint.
  return (
    <Card className="border-primary/30 bg-primary/[0.03] shadow-hero">
      <CardHeader title="Business Decision" description="AI advises. You decide." />
      <CardBody className="space-y-4">
        {alreadyDecided ? (
          <p className="text-sm text-muted-foreground">
            This mission is already completed. Re-run the evaluation above if the underlying evidence has
            changed and a new decision is needed.
          </p>
        ) : mission.status !== "awaiting_approval" ? (
          <p className="text-sm text-muted-foreground">
            A decision can only be recorded once a recommendation exists and the mission is awaiting approval
            (current status: {mission.status}).
          </p>
        ) : blockingRowCount > 0 ? (
          <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning-soft px-3 py-2.5 text-sm text-warning">
            <AlertOctagon size={16} className="shrink-0 mt-0.5" />
            <span>
              {blockingRowCount} item{blockingRowCount === 1 ? "" : "s"} in the Compliance Matrix above must be
              verified before you can save a decision — look for the "Verify" action on each flagged row.
            </span>
          </div>
        ) : (
          <>
            {/* Condensed recap -- three lines, no new data, sourced from
                the recommendation and blocker count already on the page
                above. So the decision-maker isn't relying on memory of
                what they read several screens up (docs/
                TENDER_JOURNEY_DESIGN.md §3). */}
            <div className="rounded-md border border-border bg-muted/30 px-3.5 py-3 text-sm space-y-1">
              <p>
                <span className="text-muted-foreground">Tender Assessment: </span>
                <span className="font-medium">{recommendationLabel(recommendation.recommendation_type)}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Mandatory blockers: </span>
                <span className="font-medium">
                  {mandatoryBlockerCount === 0 ? "None" : mandatoryBlockerCount}
                </span>
              </p>
              <p>
                <span className="text-muted-foreground">Overall confidence: </span>
                <span className="font-medium">
                  {recommendation.overall_confidence != null
                    ? `${Math.round(recommendation.overall_confidence * 100)}%`
                    : "—"}
                </span>
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {DECISION_OPTIONS.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setSelected(value)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
                    selected === value
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-surface hover:bg-surface-hover"
                  )}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </div>

            <Textarea
              label={`Notes${selected === "rejected" ? " (required)" : " (optional)"}`}
              placeholder="Why this decision? e.g. capacity risk, pricing, strategic fit…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />

            {selected && (
              // Grounded in a verified backend fact, not a UX flourish: no
              // reopen mechanism exists once a mission leaves
              // awaiting_approval (docs/TENDER_JOURNEY_DESIGN.md §4) -- so
              // this statement is literally true, not just emphatic.
              <p className="text-xs text-muted-foreground">
                This decision is final and cannot be changed within BidOps once saved.
              </p>
            )}

            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={!selected} loading={saving}>
                Save Decision
              </Button>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}

function StatusStat({ label, status, count }: { label: string; status: MatchStatus; count: number }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
        <Badge value={status} />
      </div>
      <p className="text-3xl font-semibold tabular-nums">{count}</p>
    </Card>
  );
}

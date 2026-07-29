import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getEvaluation, getMission, recordDecision, runEvaluation } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { recommendationLabel } from "../lib/recommendationLabels";
import { mergeRequirementContext, type MergedComplianceEntry } from "../lib/complianceMerge";
import type { BusinessDecision, ComplianceMatrixEntryRead, EvaluationResponse, MatchStatus, MissionRead } from "../api/types";
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
import { AlertOctagon, Check, ChevronDown, RefreshCw, ShieldQuestion, TrendingUp, X } from "lucide-react";
import { cn } from "../lib/cn";

const DECISION_STAGES = [
  "Loading capability library…",
  "Matching requirements against evidence…",
  "Scoring compliance and risk…",
  "Drafting executive recommendation…",
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

export default function Evaluation() {
  const { missionId } = useParams<{ missionId: string }>();
  const { notify } = useToast();
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [mission, setMission] = useState<MissionRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<MatchStatus | "all">("all");
  const [expanded, setExpanded] = useState<Record<MatchStatus, boolean>>({
    not_met: true,
    review_required: true,
    conditional: false,
    met: false,
  });

  const refresh = async () => {
    if (!missionId) return;
    setLoading(true);
    setNotFound(false);
    try {
      // Evaluation (AI analysis) and Mission (status, for the Business
      // Decision panel below) are two separate resources; both must
      // succeed for this page to render, so a single try/catch covers both.
      const [evaluation, missionResult] = await Promise.all([getEvaluation(missionId), getMission(missionId)]);
      setData(evaluation);
      setMission(missionResult);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId]);

  const handleRun = async () => {
    if (!missionId) return;
    setRunning(true);
    try {
      const result = await runEvaluation(missionId);
      setData(result);
      setNotFound(false);
      // Re-running moves the mission to awaiting_approval (or resets a
      // prior decision's completed status) -- refetch so the Business
      // Decision panel below reflects the mission's real current state.
      setMission(await getMission(missionId));
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

  const blockingIssues = useMemo(
    () => (data?.gap_analysis ?? []).filter((g) => g.mandatory && g.status === "not_met"),
    [data]
  );

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

  if (notFound || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Decision Engine</h1>
        </div>
        <Card>
          <CardBody>
            <EmptyState
              icon={TrendingUp}
              title="This mission hasn't been evaluated yet"
              description="Run the Decision Engine to match requirements against your capability library and generate a recommendation."
              action={<Button onClick={handleRun}>Run Evaluation</Button>}
            />
          </CardBody>
        </Card>
      </div>
    );
  }

  const { recommendation, compliance_matrix } = data;
  const accentBar =
    recommendation.recommendation_type === "go"
      ? "bg-success"
      : recommendation.recommendation_type === "no_go"
      ? "bg-danger"
      : "bg-warning";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Decision Engine Result</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generated {new Date(recommendation.generated_at).toLocaleString()}
          </p>
        </div>
        <Button variant="outline" size="sm" icon={<RefreshCw size={14} />} onClick={handleRun}>
          Re-run
        </Button>
      </div>

      {/* AI Decision -- the visual centerpiece of the page. Kept deliberately
          calm per the brand brief (flat surface, no gradient wash, no
          oversized warning colors): a single thin accent stripe carries the
          GO/NO-GO signal, everything else stays neutral and typographic so
          it reads as an executive decision report, not a status dashboard. */}
      <div className="relative rounded-xl border bg-surface p-6 sm:p-8 shadow-hero overflow-hidden">
        <div className={cn("absolute left-0 top-0 bottom-0 w-1.5", accentBar)} />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">AI Decision</span>
        <div className="flex flex-col md:flex-row items-start md:items-center gap-8 mt-3">
          <div className="flex-1 space-y-3 min-w-0 order-2 md:order-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-display font-semibold text-4xl tracking-tight">{recommendationLabel(recommendation.recommendation_type)}</span>
              {recommendation.risk_level && <Badge value={recommendation.risk_level} withIcon />}
            </div>
            <p className="text-sm leading-relaxed text-foreground/80 max-w-2xl">{recommendation.executive_summary}</p>
          </div>
          <div className="order-1 md:order-2 flex flex-col items-center gap-1.5 shrink-0">
            <ConfidenceRing value={recommendation.overall_confidence} size={104} />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Overall Confidence</span>
          </div>
        </div>

        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mt-8 mb-3">Key Reasons</p>
        <p className="text-sm leading-relaxed text-foreground/80 max-w-3xl">
          {recommendation.executive_summary ?? "No executive summary was generated for this evaluation."}
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8 pt-6 border-t border-border">
          <ConfidenceBar label="Document Confidence" value={recommendation.document_confidence} />
          <ConfidenceBar label="Entity Confidence" value={recommendation.entity_confidence} />
          <ConfidenceBar label="Matching Confidence" value={recommendation.matching_confidence} />
          <ConfidenceBar label="Recommendation Confidence" value={recommendation.recommendation_confidence} />
        </div>
      </div>

      {/* Risk Summary */}
      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <ShieldQuestion size={15} className="text-muted-foreground" />
              Risk Summary
            </span>
          }
        />
        <CardBody className="flex items-center gap-4">
          {recommendation.risk_level ? (
            <>
              <Badge value={recommendation.risk_level} withIcon />
              <p className="text-sm text-muted-foreground leading-relaxed">
                Overall risk assessed as <span className="font-medium text-foreground">{recommendation.risk_level}</span> based on{" "}
                {blockingIssues.length > 0
                  ? `${blockingIssues.length} unresolved mandatory requirement(s).`
                  : "no unresolved mandatory requirements."}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No risk level was returned for this evaluation.</p>
          )}
        </CardBody>
      </Card>

      {/* Compliance Summary */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Compliance Summary</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatusStat label="Met" status="met" count={statusCount(compliance_matrix, "met")} />
          <StatusStat label="Not Met" status="not_met" count={statusCount(compliance_matrix, "not_met")} />
          <StatusStat label="Review Required" status="review_required" count={statusCount(compliance_matrix, "review_required")} />
          <StatusStat label="Conditional" status="conditional" count={statusCount(compliance_matrix, "conditional")} />
        </div>
      </div>

      {/* What's actually blocking this bid -- the one thing a business
          stakeholder needs before reading rows of detail. */}
      {blockingIssues.length > 0 && (
        <Card className="border-danger/30">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <AlertOctagon size={15} className="text-danger" />
                What's Blocking This Bid
              </span>
            }
            description={`${blockingIssues.length} mandatory requirement(s) not met`}
          />
          <CardBody className="!py-2">
            <ul className="divide-y divide-border -mx-6">
              {blockingIssues.map((g) => (
                <li key={g.requirement_id} className="px-6 py-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-medium leading-relaxed">{g.description}</span>
                    <Badge value="not_met" withIcon />
                  </div>
                  {g.reason && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{g.reason}</p>}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* Compliance matrix / supporting evidence -- grouped by status
          instead of one long flat scroll, requirement text leads every
          row, raw matched evidence is tucked behind a "View evidence"
          disclosure instead of printed in full for every single row. */}
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
                        <MatrixRow key={entry.id} entry={entry} />
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <ul className="divide-y divide-border -mx-6">
              {filtered.map((entry) => (
                <MatrixRow key={entry.id} entry={entry} />
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {/* Divider is deliberate (BID_DECISION_DESIGN.md §3): everything
          above is AI Analysis, everything below is the human's own
          Business Decision. AI advises, human decides. */}
      {mission && (
        <BusinessDecisionPanel mission={mission} onDecisionRecorded={setMission} />
      )}
    </div>
  );
}

function MatrixRow({ entry }: { entry: MergedEntry }) {
  // The signature evidence trail (DESIGN_SYSTEM.md §10): Recommendation
  // (the row itself) -> Evidence -> Source Clause -> Company Document.
  // Each step only renders if the backend actually resolved it -- no
  // placeholder text stands in for a step that isn't real, per "evidence
  // First" (PRODUCT_CONSTITUTION.md §7): every claim here is traceable.
  const hasTrail = Boolean(entry.supporting_evidence || entry.source_page != null || entry.evidence_source);

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
  onDecisionRecorded,
}: {
  mission: MissionRead;
  onDecisionRecorded: (mission: MissionRead) => void;
}) {
  const { notify } = useToast();
  const [selected, setSelected] = useState<BusinessDecision | null>(null);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const alreadyDecided = mission.status === "completed";
  const canDecide = mission.status === "awaiting_approval";

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

  return (
    <Card>
      <CardHeader title="Business Decision" description="AI advises. You decide." />
      <CardBody className="space-y-4">
        {alreadyDecided ? (
          <p className="text-sm text-muted-foreground">
            This mission is already completed. Re-run the evaluation above if the underlying evidence has
            changed and a new decision is needed.
          </p>
        ) : !canDecide ? (
          <p className="text-sm text-muted-foreground">
            A decision can only be recorded once a recommendation exists and the mission is awaiting approval
            (current status: {mission.status}).
          </p>
        ) : (
          <>
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

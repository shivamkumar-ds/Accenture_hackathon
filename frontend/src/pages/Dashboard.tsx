import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getEvaluation, listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import type { EvaluationResponse, MissionRead, MissionStatus } from "../api/types";
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  CREDITS_TOTAL,
  CREDITS_USED,
  StatCard,
  StatusDonut,
  useGreeting,
} from "../components/kit";
import { recommendationLabel } from "../lib/recommendationLabels";
import { SkeletonList, SkeletonStatRow } from "../components/kit";
import { EmptyState } from "../components/kit";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileStack,
  Layers,
  Radar,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
} from "lucide-react";

const PIPELINE_STAGES: { key: MissionStatus; label: string; tone: string }[] = [
  { key: "created", label: "Uploaded", tone: "bg-muted-foreground/40" },
  { key: "running", label: "Processing", tone: "bg-info" },
  { key: "awaiting_approval", label: "Awaiting Approval", tone: "bg-warning" },
  { key: "completed", label: "Completed", tone: "bg-success" },
  { key: "archived", label: "Archived", tone: "bg-muted-foreground/20" },
];

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  const { user } = useAuth();
  const greeting = useGreeting(user?.name);
  const [missions, setMissions] = useState<MissionRead[]>([]);
  const [evaluations, setEvaluations] = useState<{ mission: MissionRead; evaluation: EvaluationResponse }[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const missionList = await listMissions();
        setMissions(missionList);

        // Aggregate real numbers across every completed mission, not just
        // the latest one -- these stand in for the reference's "Win
        // Probability"-style figures without needing a real ML model or a
        // market-wide dataset we don't have (see chat history).
        const completed = missionList.filter((m) => m.status === "completed" && m.recommendation_id);
        const results = await Promise.all(
          completed.map(async (m) => ({ mission: m, evaluation: await getEvaluation(m.id) }))
        );
        results.sort((a, b) => (b.mission.completed_at ?? "").localeCompare(a.mission.completed_at ?? ""));
        setEvaluations(results);
      } catch (err) {
        notify("error", extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeMissions = useMemo(
    () => missions.filter((m) => m.status === "running" || m.status === "created" || m.status === "awaiting_approval"),
    [missions]
  );

  const latest = evaluations[0] ?? null;

  const goCount = useMemo(
    () => evaluations.filter((e) => e.evaluation.recommendation.recommendation_type === "go").length,
    [evaluations]
  );

  const successRate = evaluations.length
    ? Math.round(
        (evaluations.filter((e) =>
          ["go", "conditional_go"].includes(e.evaluation.recommendation.recommendation_type)
        ).length /
          evaluations.length) *
          100
      )
    : null;

  const criticalGaps = useMemo(
    () =>
      evaluations.reduce(
        (sum, e) => sum + e.evaluation.gap_analysis.filter((g) => g.mandatory && g.status === "not_met").length,
        0
      ),
    [evaluations]
  );

  // Real compliance-status breakdown aggregated across every evaluated
  // mission's compliance_matrix -- same data the reference's "Requirement
  // Compliance" donut implied, just computed from what we actually have
  // instead of a static mock number.
  const complianceSegments = useMemo(() => {
    const counts = { met: 0, conditional: 0, review_required: 0, not_met: 0 };
    evaluations.forEach((e) => {
      e.evaluation.compliance_matrix.forEach((c) => {
        counts[c.status] = (counts[c.status] ?? 0) + 1;
      });
    });
    return [
      { key: "met", label: "Met", count: counts.met },
      { key: "conditional", label: "Conditional", count: counts.conditional },
      { key: "review_required", label: "Review Required", count: counts.review_required },
      { key: "not_met", label: "Not Met", count: counts.not_met },
    ];
  }, [evaluations]);
  const complianceTotal = complianceSegments.reduce((s, c) => s + c.count, 0);
  const complianceAvgPct = complianceTotal ? Math.round((complianceSegments[0].count / complianceTotal) * 100) : null;

  // Real, derived insight -- the most frequently recurring unresolved
  // requirement description across every evaluated mission. Not a
  // fabricated "AI recommendation," just an honest frequency count over
  // data we already fetched.
  const topInsight = useMemo(() => {
    const counts = new Map<string, number>();
    evaluations.forEach((e) => {
      e.evaluation.gap_analysis
        .filter((g) => g.status !== "met" && g.description)
        .forEach((g) => counts.set(g.description!, (counts.get(g.description!) ?? 0) + 1));
    });
    const entries = Array.from(counts.entries());
    if (entries.length === 0) return null;
    const [description, count] = entries.reduce((max, entry) => (entry[1] > max[1] ? entry : max));
    return { description, count };
  }, [evaluations]);

  const continueTarget = activeMissions[0] ?? null;

  // DESIGN_SYSTEM.md v1.0 §9: the dashboard should answer "what needs my
  // attention today," not "look how many tenders exist." These are the two
  // situations that genuinely require a human decision right now -- a
  // mission waiting on approval, or a mandatory requirement that isn't
  // met -- built entirely from data already fetched above, not a new
  // endpoint or a fabricated "priority score."
  const attentionItems = useMemo(() => {
    const items: {
      id: string;
      label: string;
      detail: string;
      to: string;
      tone: "warning" | "danger";
    }[] = [];

    missions
      .filter((m) => m.status === "awaiting_approval")
      .forEach((m) =>
        items.push({
          id: `approval-${m.id}`,
          label: m.mission_type,
          detail: "Awaiting your approval",
          to: `/missions/${m.id}`,
          tone: "warning",
        })
      );

    evaluations.forEach(({ mission, evaluation }) => {
      const unresolved = evaluation.gap_analysis.filter((g) => g.mandatory && g.status === "not_met").length;
      if (unresolved > 0) {
        items.push({
          id: `gap-${mission.id}`,
          label: mission.mission_type,
          detail: `${unresolved} mandatory requirement${unresolved > 1 ? "s" : ""} not met`,
          to: `/missions/${mission.id}`,
          tone: "danger",
        });
      }
    });

    return items.slice(0, 5);
  }, [missions, evaluations]);

  const pipelineCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    PIPELINE_STAGES.forEach((s) => (counts[s.key] = 0));
    missions.forEach((m) => (counts[m.status] = (counts[m.status] ?? 0) + 1));
    return counts;
  }, [missions]);
  const pipelineTotal = missions.length || 1;

  const recentEvaluations = evaluations.slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-primary mb-1">From Documents to Decisions.</p>
        <h1 className="text-2xl font-semibold tracking-tight">{greeting} 👋</h1>
        <p className="text-sm text-muted-foreground mt-1">Here's what needs your attention today.</p>
      </div>

      {/* Decision-first, not inventory-first (DESIGN_SYSTEM.md §9): this is
          the first substantive content on the page, ahead of the stat
          grid, because "what needs a decision from me" matters more than
          "how many things exist." A calm all-clear state is itself a
          meaningful, reassuring answer -- not an empty placeholder. */}
      {!loading && (
        <Card className={attentionItems.length > 0 ? "border-warning/30" : undefined}>
          <CardHeader
            title="Needs Your Attention"
            description={
              attentionItems.length > 0
                ? `${attentionItems.length} item(s) waiting on a decision`
                : "Nothing requires a decision right now"
            }
          />
          <CardBody className={attentionItems.length > 0 ? "!py-2" : undefined}>
            {attentionItems.length > 0 ? (
              <ul className="divide-y divide-border -mx-6">
                {attentionItems.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={item.to}
                      className="flex items-center justify-between gap-3 px-6 py-3 hover:bg-surface-hover transition-colors"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{item.detail}</p>
                      </div>
                      <Badge value={item.tone === "danger" ? "not_met" : "review_required"} label={item.tone === "danger" ? "Blocked" : "Pending"} withIcon />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex items-center gap-3 py-2">
                <div className="w-8 h-8 rounded-lg bg-success/10 text-success flex items-center justify-center shrink-0">
                  <CheckCircle2 size={15} />
                </div>
                <p className="text-sm text-muted-foreground">
                  No missions are awaiting approval and no mandatory requirements are unresolved.
                </p>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {loading ? (
        <SkeletonStatRow />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Active Evaluations" value={activeMissions.length} icon={<Radar size={16} />} tone="info" />
          <StatCard
            label="GO Recommendations"
            value={goCount}
            icon={<Target size={16} />}
            tone="success"
            trend={evaluations.length ? `of ${evaluations.length} evaluated` : undefined}
          />
          <StatCard label="Success Rate" value={successRate != null ? `${successRate}%` : "—"} icon={<TrendingUp size={16} />} tone="primary" />
          <StatCard
            label="Critical Gaps"
            value={criticalGaps}
            icon={<AlertTriangle size={16} />}
            tone={criticalGaps > 0 ? "warning" : "success"}
          />
          <StatCard
            label="AI Credits"
            value={`${Math.round(((CREDITS_TOTAL - CREDITS_USED) / CREDITS_TOTAL) * 100)}%`}
            icon={<Zap size={16} />}
            tone="neutral"
            trend="remaining"
          />
        </div>
      )}

      {!loading && continueTarget && (
        <Card className="border-primary/30 bg-primary/[0.03]">
          <CardBody>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-1">Continue where you left off</p>
                <p className="font-medium truncate">{continueTarget.mission_type}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Status: <Badge value={continueTarget.status} />
                </p>
              </div>
              <Link
                to={`/missions/${continueTarget.id}`}
                className="inline-flex items-center gap-1.5 h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-hover transition-colors shrink-0"
              >
                Continue <ArrowRight size={14} />
              </Link>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Two even rows instead of three independent-height columns -- every
          card in a row now matches height (`items-stretch` + `h-full` +
          `flex-1` on the body), so the grid reads as a deliberate layout
          rather than a jagged masonry of whatever each card's content
          happened to need. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        <Card className="h-full flex flex-col">
          <CardHeader title="Mission Pipeline" description={`${missions.length} total mission(s)`} />
          <CardBody className="flex-1">
            {loading ? (
              <SkeletonList rows={1} />
            ) : missions.length === 0 ? (
              <EmptyState compact icon={Radar} title="No missions yet" description="Upload a tender to start your first mission." />
            ) : (
              <div className="space-y-3">
                <div className="h-2.5 w-full rounded-full overflow-hidden flex bg-muted">
                  {PIPELINE_STAGES.map((s) => {
                    const pct = (pipelineCounts[s.key] / pipelineTotal) * 100;
                    return pct > 0 ? <div key={s.key} className={s.tone} style={{ width: `${pct}%` }} /> : null;
                  })}
                </div>
                <div className="flex flex-col gap-1.5">
                  {PIPELINE_STAGES.map((s) => (
                    <div key={s.key} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-muted-foreground">
                        <span className={`w-2 h-2 rounded-full ${s.tone}`} />
                        {s.label}
                      </span>
                      <span className="font-semibold tabular-nums">{pipelineCounts[s.key]}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        <Card className="h-full flex flex-col">
          <CardHeader title="Recent Tender Evaluations" description={evaluations.length ? `${evaluations.length} evaluated` : undefined} />
          <CardBody className="!px-0 flex-1">
            {loading ? (
              <div className="px-6">
                <SkeletonList rows={3} />
              </div>
            ) : recentEvaluations.length === 0 ? (
              <div className="px-6">
                <EmptyState
                  compact
                  icon={Sparkles}
                  title="No recommendations yet"
                  description="Upload a tender and run it through the Decision Engine to see your first recommendation here."
                  action={
                    <Link to="/tenders/new" className="text-sm font-medium text-primary hover:underline">
                      Upload a tender →
                    </Link>
                  }
                />
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {recentEvaluations.map(({ mission, evaluation }) => (
                  <li key={mission.id} className="px-6 py-3 flex items-center justify-between gap-3">
                    <Link to={`/missions/${mission.id}`} className="flex items-center gap-3 min-w-0 flex-1 group">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                        <Target size={14} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">{mission.mission_type}</p>
                        <p className="text-xs text-muted-foreground tabular-nums">
                          {new Date(mission.completed_at ?? mission.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </Link>
                    <div className="text-right shrink-0">
                      <Badge
                        value={evaluation.recommendation.recommendation_type}
                        label={recommendationLabel(evaluation.recommendation.recommendation_type)}
                        withIcon
                      />
                      {evaluation.recommendation.overall_confidence != null && (
                        <p className="text-xs text-muted-foreground mt-1 tabular-nums">
                          {Math.round(evaluation.recommendation.overall_confidence * 100)}% confidence
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card className="h-full flex flex-col">
          <CardHeader title="AI Insights" description="Derived from your evaluation history" />
          <CardBody className="flex-1">
            {loading ? (
              <SkeletonList rows={2} />
            ) : topInsight ? (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <Sparkles size={15} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Most common gap</p>
                  <p className="text-sm leading-relaxed">{topInsight.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Appeared in {topInsight.count} of {evaluations.length} evaluated mission(s)
                  </p>
                </div>
              </div>
            ) : (
              <EmptyState compact icon={Sparkles} title="No insights yet" description="Insights appear once you have evaluated missions." />
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        <Card className="h-full flex flex-col lg:col-span-1">
          <CardHeader title="Requirement Compliance" description={complianceTotal ? `${complianceTotal} requirements evaluated` : undefined} />
          <CardBody className="flex-1 flex items-center">
            {loading ? (
              <SkeletonList rows={1} />
            ) : complianceTotal === 0 ? (
              <EmptyState compact icon={TrendingUp} title="No data yet" description="Run the Decision Engine on a tender to see compliance breakdown." />
            ) : (
              <StatusDonut segments={complianceSegments} centerLabel={`${complianceAvgPct}%`} />
            )}
          </CardBody>
        </Card>

        <Card className="h-full flex flex-col lg:col-span-2">
          <CardHeader title="Quick Actions" />
          <CardBody className="flex-1">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <QuickAction to="/tenders/new" icon={FileStack} label="Upload Tender" />
              <QuickAction to="/documents" icon={FileStack} label="Upload Documents" />
              <QuickAction to="/capabilities" icon={Layers} label="Build Capabilities" />
              <QuickAction to="/missions" icon={Radar} label="Tender Workspace" />
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function QuickAction({ to, icon: Icon, label }: { to: string; icon: typeof FileStack; label: string }) {
  return (
    <Link
      to={to}
      className="flex flex-col items-start gap-2 rounded-lg border border-border p-3.5 hover:border-primary/40 hover:bg-primary/[0.03] transition-colors"
    >
      <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
        <Icon size={15} />
      </div>
      <span className="text-sm font-medium leading-tight">{label}</span>
    </Link>
  );
}

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { executeMission, getCapabilityGraph, getEvaluation, listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import type { CapabilityGraphResponse, EvaluationResponse, MissionRead, MissionStatus } from "../api/types";
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  Menu,
  MenuItem,
  SkeletonList,
  SkeletonStatRow,
  StatCard,
  useGreeting,
} from "../components/kit";
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CheckCircle2,
  FileBarChart2,
  FileSearch,
  FileUp,
  Layers,
  Loader2,
  MoreVertical,
  Radar,
  Sparkles,
} from "lucide-react";

// Real MissionStatus values, relabeled for the "Evaluation Status" column --
// Badge already maps these to consistent tones/icons app-wide.
const EVAL_STATUS_LABEL: Record<MissionStatus, string> = {
  created: "Queued",
  running: "Analysis Running",
  awaiting_approval: "Awaiting Approval",
  completed: "Completed",
  archived: "Archived",
};

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();
  const greeting = useGreeting(user?.name);
  const [missions, setMissions] = useState<MissionRead[]>([]);
  const [evaluations, setEvaluations] = useState<{ mission: MissionRead; evaluation: EvaluationResponse }[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityGraphResponse | null>(null);
  const [runningId, setRunningId] = useState<string | null>(null);

  const loadMissions = async () => {
    const missionList = await listMissions();
    setMissions(missionList);

    // Aggregate real numbers across every completed mission, not just the
    // latest one -- these stand in for the reference's summary-style
    // figures without needing a real ML model or a market-wide dataset we
    // don't have.
    const completed = missionList.filter((m) => m.status === "completed" && m.recommendation_id);
    const results = await Promise.all(
      completed.map(async (m) => ({ mission: m, evaluation: await getEvaluation(m.id) }))
    );
    results.sort((a, b) => (b.mission.completed_at ?? "").localeCompare(a.mission.completed_at ?? ""));
    setEvaluations(results);
  };

  useEffect(() => {
    (async () => {
      try {
        await Promise.all([loadMissions(), getCapabilityGraph().then(setCapabilities)]);
      } catch (err) {
        notify("error", extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const criticalGaps = useMemo(
    () =>
      evaluations.reduce(
        (sum, e) => sum + e.evaluation.gap_analysis.filter((g) => g.mandatory && g.status === "not_met").length,
        0
      ),
    [evaluations]
  );

  // DESIGN_SYSTEM.md v1.0 §9: the dashboard should answer "what needs my
  // attention today," not "look how many tenders exist." These are the two
  // situations that genuinely require a human decision right now -- a
  // mission waiting on approval, or a mandatory requirement that isn't met.
  const attentionItems = useMemo(() => {
    const items: { id: string; label: string; detail: string; to: string; tone: "warning" | "danger" }[] = [];

    missions
      .filter((m) => m.status === "awaiting_approval")
      .forEach((m) =>
        items.push({ id: `approval-${m.id}`, label: m.mission_type, detail: "Awaiting your approval", to: `/missions/${m.id}`, tone: "warning" })
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

  const runningMission = missions.find((m) => m.status === "running") ?? null;

  // "Recent Activity" -- merged from real timestamped events we already
  // have (mission uploaded, mission completed, capability record added).
  // No fabricated activity log or notification feed.
  const recentActivity = useMemo(() => {
    type Item = { id: string; icon: typeof FileUp; label: string; detail: string; at: string };
    const items: Item[] = [];

    missions.forEach((m) => {
      items.push({ id: `up-${m.id}`, icon: FileUp, label: "Tender uploaded", detail: m.mission_type, at: m.created_at });
      if (m.completed_at) {
        items.push({ id: `done-${m.id}`, icon: CheckCircle2, label: "Evaluation completed", detail: m.mission_type, at: m.completed_at });
      }
    });

    if (capabilities) {
      type AnyCapabilityEntry =
        | CapabilityGraphResponse["certifications"][number]
        | CapabilityGraphResponse["employees"][number]
        | CapabilityGraphResponse["projects"][number]
        | CapabilityGraphResponse["equipment"][number]
        | CapabilityGraphResponse["financial_records"][number];
      const named = (c: AnyCapabilityEntry) =>
        ("certification_name" in c && c.certification_name) ||
        ("name" in c && c.name) ||
        ("equipment_name" in c && c.equipment_name) ||
        "Company record";
      const allEntries: AnyCapabilityEntry[] = [
        ...capabilities.certifications,
        ...capabilities.employees,
        ...capabilities.projects,
        ...capabilities.equipment,
        ...capabilities.financial_records,
      ];
      allEntries.forEach((c) =>
        items.push({ id: `cap-${c.id}`, icon: Layers, label: "Capability added", detail: named(c), at: c.created_at })
      );
    }

    return items.sort((a, b) => b.at.localeCompare(a.at)).slice(0, 6);
  }, [missions, capabilities]);

  const recentMissions = missions.slice(0, 6);

  const handleRunFullAnalysis = async (missionId: string) => {
    setRunningId(missionId);
    try {
      await executeMission(missionId);
      notify("success", "Full analysis complete — recommendation generated.");
      await loadMissions();
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{greeting} 👋</h1>
          <p className="text-sm text-muted-foreground mt-1">Here's what's happening with your tenders today.</p>
        </div>
        {!loading && (
          <a href="#attention" className="relative shrink-0">
            <div className="w-9 h-9 rounded-lg border border-border bg-surface flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-surface-hover transition-colors">
              <Bell size={16} />
            </div>
            {attentionItems.length > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-danger text-danger-foreground text-[10px] font-bold flex items-center justify-center">
                {attentionItems.length}
              </span>
            )}
          </a>
        )}
      </div>

      {!loading && (
        <Card id="attention" className={attentionItems.length > 0 ? "border-warning/30 scroll-mt-6" : "scroll-mt-6"}>
          <CardHeader
            title="Needs Your Attention"
            description={attentionItems.length > 0 ? `${attentionItems.length} item(s) waiting on a decision` : "Nothing requires a decision right now"}
          />
          <CardBody className={attentionItems.length > 0 ? "!py-2" : undefined}>
            {attentionItems.length > 0 ? (
              <ul className="divide-y divide-border -mx-6">
                {attentionItems.map((item) => (
                  <li key={item.id}>
                    <Link to={item.to} className="flex items-center justify-between gap-3 px-6 py-3 hover:bg-surface-hover transition-colors">
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
                <p className="text-sm text-muted-foreground">No missions are awaiting approval and no mandatory requirements are unresolved.</p>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {loading ? (
        <SkeletonStatRow />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            label="Tenders"
            value={missions.length}
            icon={<FileUp size={16} />}
            tone="info"
            trend="Total Uploaded"
            linkTo="/missions"
            linkLabel="View all tenders"
          />
          <StatCard
            label="Evaluations"
            value={evaluations.length}
            icon={<CheckCircle2 size={16} />}
            tone="success"
            trend="Completed"
            linkTo="/reports"
            linkLabel="View all evaluations"
          />
          <StatCard
            label="Capability Library"
            value={capabilities?.summary.total_entities ?? 0}
            icon={<Layers size={16} />}
            tone="primary"
            trend="Capabilities Extracted"
            linkTo="/capabilities"
            linkLabel="View library"
          />
          <StatCard
            label="Reports"
            value={evaluations.length}
            icon={<FileBarChart2 size={16} />}
            tone="warning"
            trend="Reports Available"
            linkTo="/reports"
            linkLabel="View all reports"
          />
          <StatCard
            label="Critical Gaps"
            value={criticalGaps}
            icon={<AlertTriangle size={16} />}
            tone={criticalGaps > 0 ? "danger" : "success"}
            trend={criticalGaps > 0 ? "Mandatory gaps unresolved" : "None outstanding"}
            linkTo="/missions"
            linkLabel="Review gaps"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader
              title="Recent Tenders"
              action={
                <Link
                  to="/tenders/new"
                  className="inline-flex items-center gap-1.5 h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-hover transition-colors shrink-0"
                >
                  <FileUp size={14} /> Upload Tender
                </Link>
              }
            />
            <CardBody className="!px-0">
              {loading ? (
                <div className="px-6">
                  <SkeletonList rows={4} />
                </div>
              ) : recentMissions.length === 0 ? (
                <div className="px-6">
                  <EmptyState
                    compact
                    icon={Radar}
                    title="No tenders yet"
                    description="Upload a tender to start your first mission."
                    action={
                      <Link to="/tenders/new" className="text-sm font-medium text-primary hover:underline">
                        Upload a tender →
                      </Link>
                    }
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-muted-foreground uppercase tracking-wide border-b border-border">
                        <th className="px-6 py-2.5 font-medium">Tender</th>
                        <th className="px-3 py-2.5 font-medium hidden sm:table-cell">Uploaded On</th>
                        <th className="px-3 py-2.5 font-medium">Status</th>
                        <th className="px-3 py-2.5 font-medium">Evaluation Status</th>
                        <th className="px-3 py-2.5 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {recentMissions.map((m) => (
                        <tr key={m.id} className="hover:bg-surface-hover transition-colors">
                          <td className="px-6 py-3">
                            <Link to={`/missions/${m.id}`} className="flex items-center gap-3 min-w-0 group">
                              <div className="w-8 h-8 rounded-lg bg-danger-soft text-danger flex items-center justify-center shrink-0 text-[9px] font-bold">
                                PDF
                              </div>
                              <span className="font-medium truncate group-hover:text-primary transition-colors">{m.mission_type}</span>
                            </Link>
                          </td>
                          <td className="px-3 py-3 text-muted-foreground tabular-nums hidden sm:table-cell">
                            {new Date(m.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-3 py-3">
                            <span className="inline-flex items-center rounded-full bg-info-soft text-info px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide">
                              Uploaded
                            </span>
                          </td>
                          <td className="px-3 py-3">
                            <Badge value={m.status} label={EVAL_STATUS_LABEL[m.status]} withIcon />
                          </td>
                          <td className="px-3 py-3 text-right">
                            <Menu
                              align="right"
                              label={`Actions for ${m.mission_type}`}
                              trigger={
                                <span className="w-8 h-8 rounded-md flex items-center justify-center text-muted-foreground hover:bg-surface-hover hover:text-foreground">
                                  <MoreVertical size={15} />
                                </span>
                              }
                            >
                              <MenuItem icon={<FileSearch size={14} />} onClick={() => navigate(`/missions/${m.id}`)}>
                                View Details
                              </MenuItem>
                              {m.status === "created" && (
                                <MenuItem
                                  icon={<Sparkles size={14} />}
                                  onClick={() => handleRunFullAnalysis(m.id)}
                                >
                                  {runningId === m.id ? "Running…" : "Run Full Analysis"}
                                </MenuItem>
                              )}
                            </Menu>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardBody>
            {missions.length > recentMissions.length && (
              <div className="px-6 py-3 border-t border-border">
                <Link to="/missions" className="text-sm font-medium text-primary hover:underline inline-flex items-center gap-1">
                  View all tenders <ArrowRight size={13} />
                </Link>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          {/* Honest by design: the backend only tracks mission status at one
              granularity (created/running/awaiting_approval/completed/
              archived) -- there's no field for step-by-step progress or a
              live percentage, so this shows the real running mission and
              its real status rather than inventing a progress bar the
              system can't actually back up. */}
          <Card>
            <CardHeader title="Ongoing Analysis" />
            <CardBody>
              {loading ? (
                <SkeletonList rows={2} />
              ) : runningMission ? (
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <p className="text-sm font-medium truncate">{runningMission.mission_type}</p>
                    <Badge value="running" label="Analysis Running" withIcon />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 size={13} className="animate-spin text-primary shrink-0" />
                    AI engine processing — this can take a few minutes.
                  </div>
                </div>
              ) : (
                <EmptyState
                  compact
                  icon={Loader2}
                  title="Nothing running right now"
                  description="Run a full analysis from Tender Workspace to see live status here."
                />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Recent Activity" action={<Link to="/missions" className="text-xs font-medium text-primary hover:underline">View all</Link>} />
            <CardBody className="!px-0">
              {loading ? (
                <div className="px-6">
                  <SkeletonList rows={3} />
                </div>
              ) : recentActivity.length === 0 ? (
                <div className="px-6">
                  <EmptyState compact icon={Sparkles} title="No activity yet" description="Activity will appear here as you upload and evaluate tenders." />
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {recentActivity.map((a) => (
                    <li key={a.id} className="px-6 py-3 flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                        <a.icon size={14} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{a.label}</p>
                        <p className="text-xs text-muted-foreground truncate">{a.detail}</p>
                      </div>
                      <span className="text-[11px] text-muted-foreground shrink-0 tabular-nums">{new Date(a.at).toLocaleDateString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

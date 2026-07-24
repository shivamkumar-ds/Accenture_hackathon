import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { executeMission, listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import type { MissionRead, MissionStatus } from "../api/types";
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, SkeletonList } from "../components/kit";
import { cn } from "../lib/cn";
import { ArrowRight, CheckCircle2, Clock3, FileUp, Loader2, Radar } from "lucide-react";

// The brief asked for a visual "story" of the tender journey (Upload ->
// Extraction -> Matching -> Compliance -> Gap Analysis -> Decision Engine
// -> Recommendation -> Report -> Completed). The real backend only tracks
// mission status at one granularity: MissionStatus ("created" | "running"
// | "awaiting_approval" | "completed" | "archived") -- there's no field
// anywhere in the contract that records which of those nine sub-steps is
// currently active. Rather than invent progress the backend can't back up,
// this stepper uses the four real states as its stages; "archived" is
// shown as a separate end-state tag rather than a fifth stage, since it's
// a post-completion housekeeping state, not forward progress.
const STAGES: { key: MissionStatus; label: string; icon: typeof FileUp }[] = [
  { key: "created", label: "Uploaded", icon: FileUp },
  { key: "running", label: "AI Processing", icon: Loader2 },
  { key: "awaiting_approval", label: "Awaiting Approval", icon: Clock3 },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
];

function stageIndex(status: MissionStatus): number {
  if (status === "archived") return 3;
  const idx = STAGES.findIndex((s) => s.key === status);
  return idx === -1 ? 0 : idx;
}

function MissionStepper({ status }: { status: MissionStatus }) {
  const current = stageIndex(status);
  const isRunning = status === "running";
  return (
    <div className="flex items-center">
      {STAGES.map((stage, i) => {
        const reached = i <= current;
        const isCurrent = i === current && !(status === "completed" || status === "archived");
        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5 w-20">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center border-2 transition-colors",
                  reached
                    ? "bg-primary border-primary text-primary-foreground"
                    : "bg-surface border-border text-muted-foreground"
                )}
              >
                <stage.icon size={13} className={isCurrent && isRunning ? "animate-spin" : undefined} />
              </div>
              <span className={cn("text-[10px] text-center leading-tight", reached ? "text-foreground font-medium" : "text-muted-foreground")}>
                {stage.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div className={cn("h-0.5 w-6 sm:w-10 -mt-4", i < current ? "bg-primary" : "bg-border")} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Missions() {
  const [missions, setMissions] = useState<MissionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const { notify } = useToast();
  const navigate = useNavigate();

  const refresh = async () => {
    try {
      setMissions(await listMissions());
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // listMissions() returns newest-first (see mission_service.list_missions,
  // ordered by created_at.desc()) -- the upload order number shown to the
  // user should read 1, 2, 3... in the order tenders were actually uploaded,
  // so it's derived here rather than relying on array position directly.
  const total = missions.length;

  const handleRunFullAnalysis = async (missionId: string) => {
    setRunningId(missionId);
    try {
      await executeMission(missionId);
      notify("success", "Full analysis complete — recommendation generated.");
      navigate(`/missions/${missionId}`);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Tender Workspace</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Every tender's journey from upload to executive recommendation.
        </p>
      </div>

      {loading ? (
        <Card>
          <CardBody>
            <SkeletonList rows={4} />
          </CardBody>
        </Card>
      ) : missions.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState icon={Radar} title="No missions yet" description="Upload a tender to start your first mission." />
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {missions.map((m, i) => {
            const order = total - i; // upload order: 1 = first tender ever uploaded
            return (
              <Card key={m.id} className="transition-shadow hover:shadow-elevated">
                <CardBody>
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-semibold shrink-0">
                        {order}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold truncate">{m.mission_type}</p>
                        <p className="text-xs text-muted-foreground tabular-nums mt-0.5">
                          Started {new Date(m.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge value={m.status} withIcon />
                      <Link
                        to={`/missions/${m.id}`}
                        className="inline-flex items-center gap-1 text-sm text-primary font-medium hover:underline"
                      >
                        Open <ArrowRight size={13} />
                      </Link>
                    </div>
                  </div>
                  <div className="overflow-x-auto pb-1">
                    <MissionStepper status={m.status} />
                  </div>
                  {m.status === "created" && (
                    <div className="mt-5 pt-4 border-t border-border flex justify-end">
                      <Button
                        size="sm"
                        loading={runningId === m.id}
                        disabled={runningId !== null}
                        onClick={() => handleRunFullAnalysis(m.id)}
                      >
                        Run Full Analysis
                      </Button>
                    </div>
                  )}
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

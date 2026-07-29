import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { tenderDisplayName } from "../lib/tenderName";
import type { MissionRead } from "../api/types";
import { Badge, Card, CardBody, CardHeader, EmptyState, SkeletonList } from "../components/kit";
import { ArrowRight, FileBarChart2 } from "lucide-react";

// Phase 5 (docs/TENDER_JOURNEY_IMPLEMENTATION_PLAN.md): this page used to
// render its own parallel copy of the evaluation summary (hero, confidence
// bars, status counts) that had already drifted out of sync with
// Evaluation.tsx's newer grouped-matrix layout (docs/TENDER_JOURNEY_DESIGN.md
// §5). That preview -- and the "Download PDF Report" action that lived
// alongside it -- moved to the mission page itself. Reports is now a
// browse/index surface over evaluated tenders, not a second rendering of
// evaluation data: selecting a tender opens its real mission page.
export default function Reports() {
  const { notify } = useToast();
  const [loading, setLoading] = useState(true);
  const [missions, setMissions] = useState<MissionRead[]>([]);

  // A tender is reportable as soon as the AI agent has produced a
  // recommendation_id -- that's what actually means "the Decision Engine
  // has run." Mission status itself normally sits at "awaiting_approval"
  // at that point (there's no in-app approve/complete action, per Tender
  // Workspace), so gating this list on status === "completed" would hide
  // every tender that had a real, ready report.
  const reportable = useMemo(() => missions.filter((m) => m.recommendation_id), [missions]);

  useEffect(() => {
    (async () => {
      try {
        // Archived (= deleted) tenders are excluded here too -- a deleted
        // tender's report shouldn't still be listed, same as it's excluded
        // from Tender Workspace and the Dashboard.
        const list = (await listMissions()).filter((m) => m.status !== "archived");
        setMissions(list);
      } catch (err) {
        notify("error", extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Every evaluated tender's Tender Assessment -- open one to review it or download its PDF report.
        </p>
      </div>

      <Card>
        <CardHeader title="Evaluated Tenders" description={reportable.length ? `${reportable.length} available` : undefined} />
        <CardBody className="!px-0">
          {loading ? (
            <div className="px-6">
              <SkeletonList rows={4} />
            </div>
          ) : reportable.length === 0 ? (
            <div className="px-6">
              <EmptyState
                compact
                icon={FileBarChart2}
                title="No reports yet"
                description="Run the Decision Engine on a tender in Tender Workspace to generate its first report."
                action={
                  <Link to="/missions" className="text-sm font-medium text-primary hover:underline">
                    Go to Tender Workspace →
                  </Link>
                }
              />
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {reportable.map((m) => (
                <li key={m.id}>
                  <Link
                    to={`/missions/${m.id}`}
                    className="flex items-center justify-between gap-3 px-6 py-3 text-sm hover:bg-surface-hover transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{tenderDisplayName(m)}</p>
                      <p className="text-xs text-muted-foreground tabular-nums mt-0.5">
                        {new Date(m.completed_at ?? m.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge value={m.status} />
                      <ArrowRight size={14} className="text-muted-foreground" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { getCompany, getEvaluation, listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { recommendationLabel } from "../lib/recommendationLabels";
import { mergeRequirementContext } from "../lib/complianceMerge";
import { tenderDisplayName } from "../lib/tenderName";
import type { EvaluationResponse, MissionRead } from "../api/types";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ConfidenceBar,
  ConfidenceRing,
  EmptyState,
  Skeleton,
  SkeletonList,
} from "../components/kit";
import { Download, FileBarChart2 } from "lucide-react";
import { cn } from "../lib/cn";

export default function Reports() {
  const { notify } = useToast();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [missions, setMissions] = useState<MissionRead[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [companyName, setCompanyName] = useState("");

  // A tender is reportable as soon as the AI agent has produced a
  // recommendation_id -- that's what actually means "the Decision Engine
  // has run." Mission status itself normally sits at "awaiting_approval"
  // at that point (there's no in-app approve/complete action, per
  // Tender Workspace), so gating this list on status === "completed" was
  // hiding every tender that had a real, ready report.
  const reportable = useMemo(() => missions.filter((m) => m.recommendation_id), [missions]);

  useEffect(() => {
    (async () => {
      try {
        // Archived (= deleted) tenders are excluded here too -- a deleted
        // tender's report shouldn't still be selectable/downloadable, same
        // as it's excluded from Tender Workspace and the Dashboard.
        const list = (await listMissions()).filter((m) => m.status !== "archived");
        setMissions(list);
        const first = list.find((m) => m.recommendation_id);
        if (first) setSelectedId(first.id);
      } catch (err) {
        notify("error", extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!user?.company_id) return;
    getCompany(user.company_id)
      .then((c) => setCompanyName(c.name))
      .catch(() => undefined);
  }, [user?.company_id]);

  useEffect(() => {
    if (!selectedId) {
      setEvaluation(null);
      return;
    }
    setLoadingReport(true);
    getEvaluation(selectedId)
      .then(setEvaluation)
      .catch((err) => notify("error", extractErrorMessage(err)))
      .finally(() => setLoadingReport(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const selectedMission = reportable.find((m) => m.id === selectedId) ?? null;
  const merged = useMemo(
    () => (evaluation ? mergeRequirementContext(evaluation.compliance_matrix, evaluation.gap_analysis) : []),
    [evaluation]
  );

  const handleDownload = async () => {
    if (!evaluation || !selectedMission) return;
    setGeneratingPdf(true);
    try {
      const { generateEvaluationPdf } = await import("../lib/pdfReport");
      generateEvaluationPdf(evaluation, merged, {
        companyName,
        missionType: tenderDisplayName(selectedMission),
        missionId: selectedMission.id,
      });
    } catch {
      notify("error", "Couldn't generate the PDF report.");
    } finally {
      setGeneratingPdf(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select a tender to preview and download its Decision Engine report as a PDF.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <Card className="lg:col-span-1">
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
                />
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {reportable.map((m) => (
                  <li key={m.id}>
                    <button
                      onClick={() => setSelectedId(m.id)}
                      className={cn(
                        "w-full text-left px-6 py-3 text-sm transition-colors",
                        selectedId === m.id ? "bg-primary/10 text-primary font-medium" : "hover:bg-surface-hover"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate">{tenderDisplayName(m)}</p>
                        <Badge value={m.status} />
                      </div>
                      <p className="text-xs text-muted-foreground tabular-nums mt-0.5">
                        {new Date(m.completed_at ?? m.created_at).toLocaleDateString()}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          {!selectedMission ? (
            <Card>
              <CardBody>
                <EmptyState
                  icon={FileBarChart2}
                  title="Select a tender"
                  description="Choose an evaluated tender on the left to preview its report."
                />
              </CardBody>
            </Card>
          ) : loadingReport || !evaluation ? (
            <Card>
              <CardBody className="space-y-4">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-32 w-full" />
              </CardBody>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader
                  title="Report Preview"
                  description={tenderDisplayName(selectedMission)}
                  action={
                    <Button size="sm" icon={<Download size={14} />} loading={generatingPdf} onClick={handleDownload}>
                      Download PDF Report
                    </Button>
                  }
                />
                <CardBody className="space-y-6">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                    <ConfidenceRing value={evaluation.recommendation.overall_confidence} size={88} />
                    <div className="space-y-2 min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">AI Decision</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-2xl font-bold tracking-tight">
                          {recommendationLabel(evaluation.recommendation.recommendation_type)}
                        </span>
                        {evaluation.recommendation.risk_level && <Badge value={evaluation.recommendation.risk_level} withIcon />}
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed max-w-xl">
                        {evaluation.recommendation.executive_summary}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-border">
                    <ConfidenceBar label="Document Confidence" value={evaluation.recommendation.document_confidence} />
                    <ConfidenceBar label="Entity Confidence" value={evaluation.recommendation.entity_confidence} />
                    <ConfidenceBar label="Matching Confidence" value={evaluation.recommendation.matching_confidence} />
                    <ConfidenceBar label="Recommendation Confidence" value={evaluation.recommendation.recommendation_confidence} />
                  </div>

                  {/* Quick-glance rollup of the same merged compliance data the
                      Compliance Summary card below breaks out in full --
                      "Needs Review" combines review_required + conditional,
                      "Missing" is not_met, matching the Decision Screen's own
                      status vocabulary rather than inventing new labels. */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
                    <div>
                      <p className="text-xl font-semibold tabular-nums">{merged.length}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">Requirements Reviewed</p>
                    </div>
                    <div>
                      <p className="text-xl font-semibold tabular-nums text-success">
                        {merged.filter((m) => m.status === "met").length}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">Matched</p>
                    </div>
                    <div>
                      <p className="text-xl font-semibold tabular-nums text-warning">
                        {merged.filter((m) => m.status === "review_required" || m.status === "conditional").length}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">Needs Review</p>
                    </div>
                    <div>
                      <p className="text-xl font-semibold tabular-nums text-danger">
                        {merged.filter((m) => m.status === "not_met").length}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">Missing</p>
                    </div>
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Compliance Summary" description={`${merged.length} requirements`} />
                <CardBody>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {(["met", "not_met", "review_required", "conditional"] as const).map((status) => (
                      <div key={status} className="rounded-lg border border-border p-4">
                        <div className="flex items-center justify-between mb-2">
                          <Badge value={status} />
                        </div>
                        <p className="text-2xl font-semibold tabular-nums">
                          {merged.filter((m) => m.status === status).length}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardBody>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

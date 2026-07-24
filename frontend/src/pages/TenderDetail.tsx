import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getTender, runAnalysis, runEvaluation } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import type { RequirementType, TenderWithRequirements } from "../api/types";
import {
  AIProcessing,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  FilterChip,
  Skeleton,
} from "../components/kit";
import { ArrowRight, FileSearch } from "lucide-react";

const ANALYSIS_STAGES = [
  "Parsing tender document…",
  "Identifying clauses and obligations…",
  "Classifying requirement types…",
  "Scoring confidence per requirement…",
];

export default function TenderDetail() {
  const { tenderId } = useParams<{ tenderId: string }>();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [data, setData] = useState<TenderWithRequirements | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [runningDecision, setRunningDecision] = useState(false);
  const [typeFilter, setTypeFilter] = useState<RequirementType | "all">("all");

  const refresh = async () => {
    if (!tenderId) return;
    setLoading(true);
    try {
      setData(await getTender(tenderId));
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenderId]);

  const handleAnalyze = async () => {
    if (!tenderId) return;
    setAnalyzing(true);
    try {
      const result = await runAnalysis(tenderId);
      setData(result);
      notify("success", `${result.requirements.length} requirements extracted.`);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRunDecisionEngine = async () => {
    if (!data?.tender.mission_id) return;
    setRunningDecision(true);
    try {
      await runEvaluation(data.tender.mission_id);
      navigate(`/missions/${data.tender.mission_id}`);
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setRunningDecision(false);
    }
  };

  const requirementTypes = useMemo(
    () => Array.from(new Set((data?.requirements ?? []).map((r) => r.requirement_type))),
    [data]
  );

  const filteredRequirements = useMemo(() => {
    if (!data) return [];
    return typeFilter === "all" ? data.requirements : data.requirements.filter((r) => r.requirement_type === typeFilter);
  }, [data, typeFilter]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (!data) return null;

  const { tender, requirements } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{tender.tender_name ?? "Untitled Tender"}</h1>
        <p className="text-sm text-muted-foreground mt-1">{tender.organization ?? "No organization specified"}</p>
      </div>

      <Card>
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Organization</p>
              <p className="font-medium">{tender.organization ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Closing Date</p>
              <p className="font-medium">{tender.closing_date ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Status</p>
              {tender.processing_status ? <Badge value={tender.processing_status} /> : "—"}
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
                <FilterChip label="All" active={typeFilter === "all"} onClick={() => setTypeFilter("all")} />
                {requirementTypes.map((t) => (
                  <FilterChip key={t} label={t.replace(/_/g, " ")} active={typeFilter === t} onClick={() => setTypeFilter(t)} />
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
                <Button onClick={handleRunDecisionEngine} loading={runningDecision} size="lg" icon={!runningDecision ? <ArrowRight size={15} /> : undefined}>
                  Run Decision Engine
                </Button>
              </div>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}

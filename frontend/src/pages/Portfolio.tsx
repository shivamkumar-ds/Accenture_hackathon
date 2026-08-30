import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPortfolio } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { recommendationLabel } from "../lib/recommendationLabels";
import type { NotYetAnalyzedMission, OpportunitySummary, PortfolioResponse, UnableToLoadMission } from "../api/types";
import { Badge, Card, CardBody, EmptyState, SkeletonList } from "../components/kit";
import { AlertTriangle, Briefcase, Clock, HelpCircle, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "../lib/cn";

// Portfolio (approved implementation plan, Phase 3 -- Portfolio frontend).
// Deliberately a pure "API response -> render" page: every bucket
// assignment, the insight sentence, and the active/analyzed counts are all
// computed server-side (see backend/app/services/portfolio_service.py).
// This file must never recompute a recommendation bucket, aggregate
// qualification gaps, or regenerate/alter the insight text -- doing so
// would let the frontend silently diverge from the backend's single
// source of truth. See PortfolioResponse's own comments in api/types.ts.

function formatConfidence(value: number | null): string {
  // Same convention as Evaluation.tsx's own overall_confidence display
  // (Math.round(value * 100)) -- an exact percentage, never a High/
  // Medium/Low relabeling and never a second, independently-computed score.
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function OpportunityCard({ opportunity }: { opportunity: OpportunitySummary }) {
  return (
    <Link
      to={`/missions/${opportunity.mission_id}`}
      className="flex items-center justify-between gap-3 rounded-md border border-border px-4 py-3 hover:bg-surface-hover hover:border-primary/30 transition-colors"
    >
      <span className="text-sm font-medium truncate">{opportunity.tender_name ?? "Untitled Tender"}</span>
      <span className="flex items-center gap-3 shrink-0">
        <Badge
          value={opportunity.recommendation_type}
          label={recommendationLabel(opportunity.recommendation_type)}
          withIcon
        />
        <span className="text-xs font-medium text-muted-foreground tabular-nums w-28 text-right">
          {formatConfidence(opportunity.overall_confidence)} confidence
        </span>
      </span>
    </Link>
  );
}

function BucketSection({
  title,
  icon: Icon,
  opportunities,
}: {
  title: string;
  icon: typeof TrendingUp;
  opportunities: OpportunitySummary[];
}) {
  if (opportunities.length === 0) return null;
  return (
    <div>
      <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        <Icon size={13} /> {title} · {opportunities.length}
      </h2>
      <div className="space-y-2">
        {opportunities.map((o) => (
          <OpportunityCard key={o.mission_id} opportunity={o} />
        ))}
      </div>
    </div>
  );
}

// Active, but no Recommendation yet -- distinct from a bucketed opportunity.
// Never given a fabricated recommendation/confidence; shown with its real
// MissionStatus instead (Badge already maps every MissionStatus value).
function NotYetAnalyzedRow({ mission }: { mission: NotYetAnalyzedMission }) {
  return (
    <Link
      to={`/missions/${mission.mission_id}`}
      className="flex items-center justify-between gap-3 rounded-md border border-border px-4 py-3 hover:bg-surface-hover transition-colors"
    >
      <span className="text-sm font-medium truncate">{mission.tender_name ?? "Untitled Tender"}</span>
      <Badge value={mission.status} withIcon />
    </Link>
  );
}

// Active, but the evaluation bundle could not be assembled this request --
// isolated server-side so it never crashes the whole Portfolio response.
// Rendered honestly: no fabricated recommendation, no fabricated
// confidence, never silently treated as NO_GO, never silently hidden.
function UnableToLoadRow({ mission }: { mission: UnableToLoadMission }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-danger/20 bg-danger-soft px-4 py-3">
      <span className="text-sm font-medium truncate">{mission.tender_name ?? "Untitled Tender"}</span>
      <span className="flex items-center gap-1.5 text-xs font-medium text-danger shrink-0">
        <AlertTriangle size={13} /> Unable to load evaluation
      </span>
    </div>
  );
}

export default function Portfolio() {
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();

  useEffect(() => {
    (async () => {
      try {
        setData(await getPortfolio());
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
        <h1 className="text-2xl font-semibold tracking-tight">Portfolio</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Where your active opportunities stand, and what's most worth addressing across them.
        </p>
      </div>

      {loading ? (
        <Card>
          <CardBody>
            <SkeletonList rows={5} />
          </CardBody>
        </Card>
      ) : !data || data.active_count === 0 ? (
        <Card>
          <CardBody>
            <EmptyState
              icon={Briefcase}
              title="No active opportunities yet"
              description="Upload and evaluate a tender to see it appear in your portfolio."
            />
          </CardBody>
        </Card>
      ) : (
        <>
          {/* Flagship insight -- deliberately the most visually prominent
              element on the page (this is the main reason Portfolio
              exists). Rendered verbatim from the backend; not one word of
              what/why/now_what is generated or altered here. */}
          {/* Flagship + Qualification Risk Exposure share one card
              (deliberately not two/three separate cards -- see the
              STOP rule against a KPI-dashboard feel). Rendered as two
              independent conditionals rather than nesting the second
              inside the first: they can be independently present --
              e.g. an all-clean portfolio (zero qualification gaps
              anywhere) has no flagship (nothing to name as "most
              common") but DOES have a real, honest "0 of M" exposure
              result, which must never be hidden just because the
              flagship happened to have nothing to say. */}
          {(data.insight || data.qualification_risk_exposure) && (
            <Card className="border-primary/30 bg-primary/5">
              <CardBody className="space-y-2">
                {data.insight && (
                  <>
                    <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-primary">
                      <Sparkles size={13} /> Flagship Insight
                    </div>
                    <p className="text-base font-semibold tracking-tight">{data.insight.what}</p>
                    <p className="text-sm text-muted-foreground">{data.insight.why}</p>
                    <p className="text-sm font-medium">{data.insight.now_what}</p>
                  </>
                )}

                {/* Qualification Risk Exposure -- second insight, visually
                    subordinate to the flagship (smaller text, no icon-led
                    header of its own). Answers a different question (HOW
                    MANY opportunities are affected by any mandatory gap)
                    than the flagship (WHAT single requirement type is
                    most common) -- rendered verbatim from the backend,
                    never recomputed here. Present even when it reports
                    zero exposure; that is a real, honest result. */}
                {data.qualification_risk_exposure && (
                  <p
                    className={cn(
                      "text-xs text-muted-foreground",
                      data.insight && "pt-2 mt-2 border-t border-primary/20"
                    )}
                  >
                    {data.qualification_risk_exposure.what}
                  </p>
                )}
              </CardBody>
            </Card>
          )}

          <Card>
            <CardBody className="space-y-6">
              <BucketSection title="Prioritize" icon={TrendingUp} opportunities={data.prioritize} />
              <BucketSection title="Review" icon={HelpCircle} opportunities={data.review} />
              <BucketSection title="Deprioritize" icon={TrendingDown} opportunities={data.deprioritize} />

              {data.not_yet_analyzed.length > 0 && (
                <div>
                  <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                    <Clock size={13} /> Not Yet Analyzed · {data.not_yet_analyzed.length}
                  </h2>
                  <div className="space-y-2">
                    {data.not_yet_analyzed.map((m) => (
                      <NotYetAnalyzedRow key={m.mission_id} mission={m} />
                    ))}
                  </div>
                </div>
              )}

              {data.unable_to_load.length > 0 && (
                <div>
                  <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                    <AlertTriangle size={13} className="text-danger" /> Unable to Load · {data.unable_to_load.length}
                  </h2>
                  <div className="space-y-2">
                    {data.unable_to_load.map((m) => (
                      <UnableToLoadRow key={m.mission_id} mission={m} />
                    ))}
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}

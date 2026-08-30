import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getEvaluation, getPortfolio, listMissions } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { tenderDisplayName } from "../lib/tenderName";
import { recommendationLabel } from "../lib/recommendationLabels";
import { cn } from "../lib/cn";
import type { EvaluationResponse, MissionRead, PortfolioResponse, RecommendationType } from "../api/types";
import { Badge, Card, CardBody, CardHeader, SkeletonList, SkeletonStatRow, useGreeting } from "../components/kit";
import { ArrowDown, ArrowRight } from "lucide-react";

// Pipeline Decision legend dots -- same four RecommendationType values used
// everywhere else in the product (Badge's semanticTone map, recommendationLabel),
// just given a solid dot color instead of Badge's soft pill background.
const DECISION_SEGMENTS: { key: RecommendationType; toneClass: string }[] = [
  { key: "go", toneClass: "bg-success" },
  { key: "conditional_go", toneClass: "bg-warning" },
  { key: "review", toneClass: "bg-info" },
  { key: "no_go", toneClass: "bg-danger" },
];

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const { notify } = useToast();
  // Name dropped from the greeting deliberately (polish pass) -- "Good
  // afternoon 👋" only, subtitle unchanged. useGreeting still supports a
  // name arg for any future caller that wants it.
  const greeting = useGreeting();
  const [missions, setMissions] = useState<MissionRead[]>([]);
  const [evaluations, setEvaluations] = useState<{ mission: MissionRead; evaluation: EvaluationResponse }[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);

  const loadMissions = async () => {
    // Archived (= deleted, see Missions.tsx's "delete tender" -> archive_mission)
    // missions are excluded from every Dashboard view -- same as Tender
    // Workspace's default view. list_missions() has no status filter,
    // applied client-side.
    const missionList = (await listMissions()).filter((m) => m.status !== "archived");
    setMissions(missionList);

    // A mission is "reportable"/evaluated as soon as the Decision Engine has
    // produced a recommendation_id. Mission status itself normally sits at
    // "awaiting_approval" at that point (there's no in-app approve/complete
    // action yet), so gating this on status === "completed" was undercounting
    // every evaluation that had a real, ready report.
    const reportable = missionList.filter((m) => m.recommendation_id);
    const results = await Promise.all(
      reportable.map(async (m) => ({ mission: m, evaluation: await getEvaluation(m.id) }))
    );
    results.sort((a, b) => (b.mission.completed_at ?? "").localeCompare(a.mission.completed_at ?? ""));
    setEvaluations(results);
  };

  useEffect(() => {
    (async () => {
      try {
        await Promise.all([loadMissions(), getPortfolio().then(setPortfolio)]);
      } catch (err) {
        notify("error", extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // "Active" mirrors Portfolio's own active_count -- falls back to the
  // client-side non-archived mission count only if the portfolio call
  // hasn't resolved yet (both fetched in the same Promise.all above, so
  // this only matters for one render before loading flips to false).
  const activeCount = portfolio?.active_count ?? missions.length;

  // "Pursuable" reuses the exact same live-recomputed recommendation_type
  // every evaluation already carries (see backend/app/api/v1/evaluation.py
  // _build_response -- recommendation.recommendation_type is recomputed
  // live on every read, never the possibly-stale persisted value). Proceed
  // (go) and Proceed With Conditions (conditional_go) are the two
  // recommendation types a company can actually act on; plain "review"
  // (undecided) and "no_go" are not counted as pursuable.
  const pursuableCount = useMemo(
    () =>
      evaluations.filter((e) => {
        const t = e.evaluation.recommendation.recommendation_type;
        return t === "go" || t === "conditional_go";
      }).length,
    [evaluations]
  );

  // "Deprioritized" = analyzed opportunities whose live recommendation is
  // specifically no_go -- distinct from Portfolio's broader "deprioritize"
  // bucket only in that this Dashboard consistently keys every number off
  // recommendation_type directly (see pursuableCount's comment above),
  // never off Portfolio's bucket grouping.
  const deprioritizedCount = useMemo(
    () => evaluations.filter((e) => e.evaluation.recommendation.recommendation_type === "no_go").length,
    [evaluations]
  );

  // The single most-confident pursuable opportunity, for the hero panel's
  // "what does pursuable actually look like" highlight. Never invents a
  // name when nothing is pursuable -- the panel shows an honest "none
  // currently pursuable" line instead (see JSX below).
  const topPursuable = useMemo(() => {
    const pursuable = evaluations.filter((e) => {
      const t = e.evaluation.recommendation.recommendation_type;
      return t === "go" || t === "conditional_go";
    });
    if (pursuable.length === 0) return null;
    return pursuable.reduce((best, e) =>
      (e.evaluation.recommendation.overall_confidence ?? -1) > (best.evaluation.recommendation.overall_confidence ?? -1)
        ? e
        : best
    );
  }, [evaluations]);

  // Pursuit-decision distribution across analyzed opportunities, keyed by
  // the same live recommendation_type used above -- not Portfolio's
  // prioritize/review/deprioritize buckets, which deliberately fold
  // "review" (undecided) and "conditional_go" (Proceed With Conditions)
  // into one "review" bucket. Keeping the four real recommendation types
  // distinct here keeps this distribution consistent with the Pursuable/
  // Deprioritized numbers above, which also key off recommendation_type
  // directly.
  const recommendationDistribution = useMemo(() => {
    const counts: Record<RecommendationType, number> = { go: 0, conditional_go: 0, review: 0, no_go: 0 };
    evaluations.forEach((e) => {
      counts[e.evaluation.recommendation.recommendation_type] += 1;
    });
    return counts;
  }, [evaluations]);

  const recentMissions = missions.slice(0, 6);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{greeting} 👋</h1>
        <p className="text-sm text-muted-foreground mt-1">Understand your opportunity pipeline and what is blocking growth.</p>
      </div>

      {/* Opportunity Growth Pulse -- the hero panel. Every number here is
          either portfolio.active_count (live from GET /api/v1/portfolio)
          or a plain client-side filter over evaluations[] (the same live-
          recomputed recommendation_type used throughout this page) -- no
          new metric, no new backend call, no recomputed business logic. */}
      {loading ? (
        <SkeletonStatRow />
      ) : (
        <Card>
          <CardBody className="space-y-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">Opportunity Growth Pulse</p>
                <p className="text-sm text-muted-foreground mt-1">
                  How ready is the company to pursue its current opportunities?
                </p>
              </div>
              <span className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-info-soft text-info px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-info" /> Live Pipeline
              </span>
            </div>

            <div className="grid grid-cols-3 divide-x divide-border">
              <div className="text-center px-2">
                <p className="text-4xl font-bold tabular-nums">{activeCount}</p>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mt-1">
                  Active Opportunities
                </p>
              </div>
              <div className="text-center px-2">
                <p className="text-4xl font-bold tabular-nums text-success">{pursuableCount}</p>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mt-1">Pursuable</p>
              </div>
              <div className="text-center px-2">
                <p className="text-4xl font-bold tabular-nums text-danger">{deprioritizedCount}</p>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mt-1">
                  Deprioritized
                </p>
              </div>
            </div>

            {evaluations.length > 0 && (
              <div className="flex flex-col items-center gap-2 pt-4 border-t border-border">
                <ArrowDown size={14} className="text-muted-foreground" />
                {topPursuable ? (
                  <Link
                    to={`/missions/${topPursuable.mission.id}`}
                    className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                  >
                    <Badge
                      value={topPursuable.evaluation.recommendation.recommendation_type}
                      label={recommendationLabel(topPursuable.evaluation.recommendation.recommendation_type)}
                      withIcon
                    />
                    <span className="text-sm font-medium">
                      {tenderDisplayName(topPursuable.mission)}
                      {topPursuable.evaluation.recommendation.overall_confidence != null &&
                        ` · ${Math.round(topPursuable.evaluation.recommendation.overall_confidence * 100)}%`}
                    </span>
                  </Link>
                ) : (
                  <p className="text-sm text-muted-foreground">No opportunity is currently pursuable.</p>
                )}
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Pipeline Decision + Key Business Insight -- deliberately two
          compact cards, not a new page and not a duplicate of Portfolio.tsx's
          own bucket lists. The decision split reads recommendationDistribution
          (derived above from the same live recommendation_type Portfolio
          uses); the insight card renders portfolio.insight.why/.now_what
          verbatim -- not one word generated here, same rule Portfolio.tsx's
          own comment states for its identical rendering of the same field. */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="flex flex-col">
          <CardHeader title="Pipeline Decision" description="How the active pipeline splits by pursuit decision." />
          <CardBody>
            {loading ? (
              <SkeletonList rows={2} />
            ) : evaluations.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No opportunities evaluated yet — run a full analysis to see the pursuit-decision split here.
              </p>
            ) : (
              <ul className="space-y-2.5">
                {DECISION_SEGMENTS.filter((s) => recommendationDistribution[s.key] > 0).map((s) => (
                  <li key={s.key} className="flex items-center gap-2 text-sm">
                    <span className={cn("w-2.5 h-2.5 rounded-full shrink-0", s.toneClass)} />
                    <span className="text-muted-foreground">{recommendationLabel(s.key)}</span>
                    <span className="font-semibold tabular-nums ml-auto">{recommendationDistribution[s.key]}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card className="flex flex-col">
          <CardHeader title="Key Business Insight" description="What's most worth addressing across the pipeline right now." />
          <CardBody className="space-y-3">
            {loading ? (
              <SkeletonList rows={2} />
            ) : portfolio?.insight ? (
              <>
                <p className="text-sm font-semibold tracking-tight">{portfolio.insight.why}</p>
                {portfolio.analyzed_count > 0 && (
                  <div>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{
                          width: `${(portfolio.insight.affected_mission_ids.length / portfolio.analyzed_count) * 100}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {portfolio.insight.affected_mission_ids.length} / {portfolio.analyzed_count} opportunities affected
                    </p>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">{portfolio.insight.now_what}</p>
              </>
            ) : portfolio && portfolio.analyzed_count > 0 ? (
              <p className="text-sm text-muted-foreground">
                No common qualification blocker detected across analyzed opportunities.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Evaluate a tender to see the leading qualification blocker across your pipeline here.
              </p>
            )}
            {!loading && (
              <Link
                to="/action-center"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline pt-1"
              >
                Turn this insight into action <ArrowRight size={13} />
              </Link>
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Recent Opportunities" />
        <CardBody className="!px-0">
          {loading ? (
            <div className="px-6">
              <SkeletonList rows={3} />
            </div>
          ) : recentMissions.length === 0 ? (
            <p className="px-6 text-sm text-muted-foreground">Upload a tender to see it appear here.</p>
          ) : (
            <ul className="divide-y divide-border">
              {recentMissions.map((m) => {
                const evalEntry = evaluations.find((e) => e.mission.id === m.id);
                return (
                  <li key={m.id}>
                    <Link
                      to={`/missions/${m.id}`}
                      className="flex items-center justify-between gap-3 px-6 py-3 hover:bg-surface-hover transition-colors"
                    >
                      <span className="text-sm font-medium truncate">{tenderDisplayName(m)}</span>
                      {evalEntry ? (
                        <Badge
                          value={evalEntry.evaluation.recommendation.recommendation_type}
                          label={recommendationLabel(evalEntry.evaluation.recommendation.recommendation_type)}
                          withIcon
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground shrink-0">Not yet evaluated</span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
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
  );
}

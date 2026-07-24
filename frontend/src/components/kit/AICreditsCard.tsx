import { Sparkles } from "lucide-react";

// Frontend Placeholder -- static values only, no backend metering exists
// yet. Wired with real click handlers (rather than dead buttons) so the
// preview is honest about being a preview: clicking either action tells
// the user billing isn't live yet instead of doing nothing silently.
// Backend Required Later: a real credits-ledger endpoint + plan/billing API.
export const CREDITS_USED = 2450;
export const CREDITS_TOTAL = 3000;
const EVALUATIONS_REMAINING = Math.round((CREDITS_TOTAL - CREDITS_USED) / (CREDITS_TOTAL / 80));

export function AICreditsCard({ onUpgrade, onPurchase }: { onUpgrade?: () => void; onPurchase?: () => void }) {
  const pct = Math.round((CREDITS_USED / CREDITS_TOTAL) * 100);
  return (
    <div className="rounded-lg border border-border bg-surface p-3.5 space-y-3">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
          <Sparkles size={12} />
          Enterprise Plan
        </span>
      </div>
      <div>
        <div className="flex items-baseline justify-between mb-1.5">
          <span className="text-xs font-medium text-muted-foreground">AI Credits</span>
          <span className="text-xs font-semibold tabular-nums">
            {CREDITS_USED.toLocaleString()} / {CREDITS_TOTAL.toLocaleString()}
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-[11px] text-muted-foreground mt-1.5">
          ~{EVALUATIONS_REMAINING} tender evaluations remaining · renews in 17 days
        </p>
      </div>
      <div className="flex items-center gap-2 pt-0.5">
        <button
          onClick={onUpgrade}
          className="flex-1 h-7 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary-hover transition-colors"
        >
          Upgrade Plan
        </button>
        <button
          onClick={onPurchase}
          className="flex-1 h-7 rounded-md text-xs font-medium border border-border hover:bg-surface-hover transition-colors"
        >
          Buy Credits
        </button>
      </div>
    </div>
  );
}

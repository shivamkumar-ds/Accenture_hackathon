import { cn } from "../../lib/cn";
import { CheckCircle2, XCircle, HelpCircle, AlertCircle, type LucideIcon } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const toneClasses: Record<Tone, string> = {
  success: "bg-success-soft text-success border-success/20",
  warning: "bg-warning-soft text-warning border-warning/20",
  danger: "bg-danger-soft text-danger border-danger/20",
  info: "bg-info-soft text-info border-info/20",
  neutral: "bg-muted text-muted-foreground border-border",
};

// Central semantic mapping -- every status/risk/recommendation value used
// anywhere in the product maps here ONCE, so tone is always consistent
// regardless of which page renders it.
const semanticTone: Record<string, Tone> = {
  met: "success", go: "success", low: "success", completed: "success", active: "success", verified: "success",
  conditional: "warning", conditional_go: "warning", medium: "warning", review: "warning", review_required: "warning", pending: "neutral", stale: "warning", processing: "info",
  not_met: "danger", no_go: "danger", critical: "danger", high: "danger", failed: "danger", expired: "danger",
  running: "info", created: "neutral", awaiting_approval: "warning", archived: "neutral", current: "success",
  mandatory: "neutral",
};

const statusIcon: Record<string, LucideIcon> = {
  met: CheckCircle2,
  go: CheckCircle2,
  not_met: XCircle,
  no_go: XCircle,
  review_required: HelpCircle,
  review: HelpCircle,
  conditional: AlertCircle,
  conditional_go: AlertCircle,
};

export function Badge({ value, withIcon = false, label }: { value: string; withIcon?: boolean; label?: string }) {
  const tone = semanticTone[value] ?? "neutral";
  const Icon = statusIcon[value];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide whitespace-nowrap",
        toneClasses[tone]
      )}
    >
      {withIcon && Icon && <Icon size={11} />}
      {/* `label` overrides the displayed text (e.g. "go" -> "Proceed") while
          tone/icon still key off the real backend `value` -- presentation
          only, the raw enum value driving styling never changes. */}
      {label ?? value.replace(/_/g, " ")}
    </span>
  );
}

export function Dot({ value }: { value: string }) {
  const tone = semanticTone[value] ?? "neutral";
  const dotColor: Record<Tone, string> = {
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-danger",
    info: "bg-info",
    neutral: "bg-muted-foreground",
  };
  return <span className={cn("inline-block w-1.5 h-1.5 rounded-full", dotColor[tone])} />;
}

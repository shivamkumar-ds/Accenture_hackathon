import type { HTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/cn";

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("bg-surface border border-border rounded-lg shadow-card", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-border">
      <div>
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("px-6 py-5", className)}>{children}</div>;
}

type StatTone = "primary" | "success" | "warning" | "danger" | "info" | "neutral";

const statToneClasses: Record<StatTone, string> = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
  neutral: "bg-muted text-muted-foreground",
};

export function StatCard({
  label,
  value,
  icon,
  trend,
  tone = "neutral",
  linkTo,
  linkLabel,
}: {
  label: string;
  value: string | number;
  icon?: ReactNode;
  trend?: string;
  tone?: StatTone;
  // Optional "View all X ->" footer link -- additive, every existing
  // caller that doesn't pass these renders exactly as before.
  linkTo?: string;
  linkLabel?: string;
}) {
  return (
    <Card className="p-3 transition-shadow hover:shadow-elevated flex gap-2.5">
      {icon && (
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 [&_svg]:w-3.5 [&_svg]:h-3.5", statToneClasses[tone])}>
          {icon}
        </div>
      )}
      <div className="min-w-0 flex-1 flex flex-col">
        <p className="text-[11px] font-medium text-muted-foreground leading-tight">{label}</p>
        <p className="text-lg font-bold tracking-tight tabular-nums mt-0.5">{value}</p>
        {/* Plain text wrapping (not flex+truncate) -- the arrow is a
            regular character in the same text flow as the label, so on a
            narrow card the whole line just reflows to a second line like
            normal text instead of either getting cut off or having the
            arrow orphaned on its own line (the flex-layout version's
            problem). */}
        {trend && <p className="text-[11px] text-muted-foreground mt-1 leading-snug">{trend}</p>}
        {linkTo && (
          <Link to={linkTo} className="text-[11px] font-medium text-primary hover:underline mt-1.5 leading-snug">
            {linkLabel ?? "View all"} <span aria-hidden="true">→</span>
          </Link>
        )}
      </div>
    </Card>
  );
}

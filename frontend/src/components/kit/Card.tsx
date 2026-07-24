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
    <Card className="p-4 transition-shadow hover:shadow-elevated flex flex-col">
      <p className="text-xs font-medium text-muted-foreground leading-tight mb-2.5">{label}</p>
      <div className="flex items-center gap-3">
        {icon && (
          <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", statToneClasses[tone])}>
            {icon}
          </div>
        )}
        <p className="text-2xl font-bold tracking-tight tabular-nums">{value}</p>
      </div>
      {trend && <p className="text-xs text-muted-foreground mt-2">{trend}</p>}
      {linkTo && (
        <Link
          to={linkTo}
          className="text-xs font-medium text-primary hover:underline mt-2.5 inline-flex items-center gap-1"
        >
          {linkLabel ?? "View all"} <span aria-hidden="true">→</span>
        </Link>
      )}
    </Card>
  );
}

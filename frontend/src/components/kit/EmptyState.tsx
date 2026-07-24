import type { LucideIcon } from "lucide-react";
import { cn } from "../../lib/cn";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact = false,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** Tighter padding for use inside half-width / grid layouts, so an empty
      card doesn't force a page taller than the viewport needs it to be. */
  compact?: boolean;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center text-center px-6", compact ? "py-7" : "py-14")}>
      <div className={cn("rounded-full bg-muted flex items-center justify-center mb-3", compact ? "w-9 h-9" : "w-12 h-12 mb-4")}>
        <Icon size={compact ? 16 : 20} className="text-muted-foreground" />
      </div>
      <h3 className="text-sm font-semibold">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

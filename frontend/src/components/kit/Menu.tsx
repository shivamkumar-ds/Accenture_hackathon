import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export function Menu({ trigger, children, align = "right" }: { trigger: ReactNode; children: ReactNode; align?: "left" | "right" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex items-center">
        {trigger}
      </button>
      {open && (
        <div
          className={cn(
            "absolute top-full mt-2 w-56 rounded-lg border border-border bg-surface shadow-elevated py-1.5 z-50 animate-fade-in",
            align === "right" ? "right-0" : "left-0"
          )}
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function MenuItem({ icon, children, onClick, danger = false }: { icon?: ReactNode; children: ReactNode; onClick?: () => void; danger?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2.5 px-3.5 py-2 text-sm text-left transition-colors",
        danger ? "text-danger hover:bg-danger-soft" : "text-foreground hover:bg-surface-hover"
      )}
    >
      {icon}
      {children}
    </button>
  );
}

export function MenuDivider() {
  return <div className="h-px bg-border my-1.5" />;
}

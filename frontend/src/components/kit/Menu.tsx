import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn } from "../../lib/cn";

const PANEL_WIDTH = 224; // w-56

export function Menu({
  trigger,
  children,
  align = "right",
  label,
}: {
  trigger: ReactNode;
  children: ReactNode;
  align?: "left" | "right";
  /** Accessible name for the trigger button — e.g. "Account menu". RC-1 audit finding C1: this
      dropdown had no accessible name or expanded-state signal for screen reader users. */
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current && !triggerRef.current.contains(target) &&
        panelRef.current && !panelRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    // Closes on scroll/resize instead of trying to keep a fixed-position
    // portal panel glued to a trigger that just moved -- simplest correct
    // behavior, matches how most dropdown libraries handle this.
    const close = () => setOpen(false);
    document.addEventListener("mousedown", handler);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("mousedown", handler);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [open]);

  function toggle() {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const left = align === "right" ? rect.right - PANEL_WIDTH : rect.left;
      const clampedLeft = Math.max(8, Math.min(left, window.innerWidth - PANEL_WIDTH - 8));
      setCoords({ top: rect.bottom + 8, left: clampedLeft });
    }
    setOpen((o) => !o);
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className="flex items-center"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={label}
      >
        {trigger}
      </button>
      {/* Rendered into document.body via portal, positioned with `fixed`
          coordinates computed from the trigger's real screen position --
          this is the real fix for the panel getting clipped/invisible
          inside any scrollable or overflow-hidden ancestor (e.g. a table
          wrapped in overflow-x-auto), since it no longer lives inside
          that ancestor's box at all. */}
      {open &&
        coords &&
        createPortal(
          <div
            ref={panelRef}
            style={{ position: "fixed", top: coords.top, left: coords.left, width: PANEL_WIDTH }}
            className={cn("rounded-lg border border-border bg-surface shadow-elevated py-1.5 z-[100] animate-fade-in")}
            onClick={() => setOpen(false)}
          >
            {children}
          </div>,
          document.body
        )}
    </>
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

import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/cn";
import { Button } from "./Button";

/**
 * BidOps' own confirmation modal -- replaces window.confirm() for
 * destructive actions (native browser dialogs can't be styled, block the
 * whole tab including any in-flight async state, and give no way to show
 * a "request in progress" state on the destructive button). Deliberately
 * generic (title/description/confirm label are all props) rather than a
 * one-off "delete tender" dialog, so any future destructive-confirmation
 * need in the app can reuse this instead of reaching for window.confirm()
 * again.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  // Escape closes -- same convention as Combobox's own panel. Not wired
  // to close on backdrop click while a request is in flight, so an
  // accidental click outside can't lose track of a destructive action
  // that's already running.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onCancel();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, loading, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/20 animate-fade-in"
      onClick={() => !loading && onCancel()}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-lg border border-border bg-surface shadow-elevated"
      >
        <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-1">
          <h2 id="confirm-dialog-title" className="text-sm font-semibold tracking-tight">
            {title}
          </h2>
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            aria-label="Close"
            className="text-muted-foreground hover:text-foreground transition shrink-0 disabled:opacity-50"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-5 py-3 text-sm text-muted-foreground leading-relaxed">{description}</div>
        <div className="flex items-center justify-end gap-2.5 px-5 pb-5 pt-2">
          <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant={danger ? "danger" : "primary"}
            size="sm"
            loading={loading}
            onClick={onConfirm}
            className={cn(loading && "cursor-wait")}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

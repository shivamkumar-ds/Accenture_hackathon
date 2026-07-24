import { cn } from "../../lib/cn";

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: () => void; label?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onChange}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        checked ? "bg-primary" : "bg-muted"
      )}
    >
      <span
        className={cn(
          "inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow-xs transition-transform duration-200",
          checked ? "translate-x-[22px]" : "translate-x-[3px]"
        )}
      />
    </button>
  );
}

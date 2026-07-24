import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "../../lib/cn";

const fieldBase =
  "block w-full rounded-md border border-input bg-surface px-3 py-2 text-sm placeholder:text-muted-foreground/70 " +
  "focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-shadow";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  // Optional leading icon / trailing element (e.g. a show/hide password
  // toggle) -- additive and backward compatible, every existing caller
  // that doesn't pass these renders exactly as before.
  icon?: LucideIcon;
  trailing?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, icon: Icon, trailing, className, ...props }, ref) => (
    <label className="block">
      {label && <span className="text-xs font-medium text-foreground/90 mb-1.5 block">{label}</span>}
      <div className="relative">
        {Icon && (
          <Icon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
        )}
        <input ref={ref} className={cn(fieldBase, Icon && "pl-9", trailing && "pr-9", className)} {...props} />
        {trailing && <div className="absolute right-3 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
      {hint && <span className="text-xs text-muted-foreground mt-1 block">{hint}</span>}
    </label>
  )
);
Input.displayName = "Input";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ label, className, children, ...props }, ref) => (
  <label className="block">
    {label && <span className="text-xs font-medium text-foreground/90 mb-1.5 block">{label}</span>}
    <select ref={ref} className={cn(fieldBase, "cursor-pointer", className)} {...props}>
      {children}
    </select>
  </label>
));
Select.displayName = "Select";

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="text-xs font-medium text-foreground/90 mb-1.5 block">{label}</span>
      {children}
    </div>
  );
}

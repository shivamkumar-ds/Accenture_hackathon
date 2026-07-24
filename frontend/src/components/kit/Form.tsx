import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const fieldBase =
  "block w-full rounded-md border border-input bg-surface px-3 py-2 text-sm placeholder:text-muted-foreground/70 " +
  "focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-shadow";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({ label, hint, className, ...props }, ref) => (
  <label className="block">
    {label && <span className="text-xs font-medium text-foreground/90 mb-1.5 block">{label}</span>}
    <input ref={ref} className={cn(fieldBase, className)} {...props} />
    {hint && <span className="text-xs text-muted-foreground mt-1 block">{hint}</span>}
  </label>
));
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

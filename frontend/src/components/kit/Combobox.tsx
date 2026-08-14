import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "../../lib/cn";

const fieldBase =
  "block w-full rounded-md border border-input bg-surface px-3 py-2 text-sm placeholder:text-muted-foreground/70 " +
  "focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition-shadow";

/**
 * Searchable single-select dropdown -- a native <select> has no way to
 * filter a long option list by typing, which the tender category list
 * needs (Combobox pattern: button trigger + search input + filtered
 * option list, closes on outside click/Escape). Kept self-contained
 * (no portal) since it's only ever used inside a normal, non-clipped
 * form layout, unlike Menu.tsx's account-menu case.
 */
export function Combobox({
  label,
  value,
  onChange,
  options,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
  searchPlaceholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  // Opens upward when there isn't enough room below the trigger for the
  // panel (roughly its own height, ~260px with the search box + option
  // list) but there is room above -- e.g. this field sitting near the
  // bottom of a form/card, where opening downward would spill past the
  // card edge or get clipped. Recomputed each time the panel opens
  // rather than tracked continuously, since it only matters at open time.
  const [openUpward, setOpenUpward] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    const PANEL_HEIGHT_ESTIMATE = 260;
    const trigger = rootRef.current?.getBoundingClientRect();
    if (trigger) {
      const spaceBelow = window.innerHeight - trigger.bottom;
      const spaceAbove = trigger.top;
      setOpenUpward(spaceBelow < PANEL_HEIGHT_ESTIMATE && spaceAbove > spaceBelow);
    }
    // Focus the search box the moment the panel opens, so typing to
    // filter works immediately without an extra click.
    requestAnimationFrame(() => searchRef.current?.focus());
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const filtered = options.filter((o) => o.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="block" ref={rootRef}>
      {label && <span className="text-xs font-medium text-foreground/90 mb-1.5 block">{label}</span>}
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="listbox"
          aria-expanded={open}
          className={cn(
            fieldBase,
            "flex items-center justify-between gap-2 text-left cursor-pointer",
            !value && "text-muted-foreground/70"
          )}
        >
          <span className="truncate">{value || placeholder}</span>
          <ChevronDown size={14} className={cn("shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
        </button>

        {open && (
          <div
            role="listbox"
            className={cn(
              "absolute z-20 w-full rounded-md border border-border bg-surface shadow-elevated overflow-hidden animate-fade-in",
              openUpward ? "bottom-full mb-1.5" : "top-full mt-1.5"
            )}
          >
            <div className="relative border-b border-border">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={searchRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pl-8 pr-2.5 py-2 text-sm bg-transparent focus:outline-none"
              />
            </div>
            <ul className="max-h-56 overflow-y-auto py-1">
              {filtered.length === 0 && (
                <li className="px-3 py-2 text-sm text-muted-foreground">No matches</li>
              )}
              {filtered.map((option) => (
                <li key={option}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={option === value}
                    onClick={() => {
                      onChange(option);
                      setOpen(false);
                    }}
                    className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-left hover:bg-surface-hover"
                  >
                    <span className="truncate">{option}</span>
                    {option === value && <Check size={14} className="text-primary shrink-0" />}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

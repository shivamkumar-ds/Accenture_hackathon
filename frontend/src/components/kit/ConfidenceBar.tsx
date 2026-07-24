import { cn } from "../../lib/cn";

function toneForValue(pct: number) {
  if (pct >= 85) return { bar: "bg-success", text: "text-success" };
  if (pct >= 60) return { bar: "bg-warning", text: "text-warning" };
  return { bar: "bg-danger", text: "text-danger" };
}

export function ConfidenceBar({ label, value }: { label: string; value: number | null }) {
  const pct = value == null ? null : Math.round(value * 100);
  const tone = toneForValue(pct ?? 0);
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={cn("text-xs font-semibold tabular-nums", pct == null ? "text-muted-foreground" : tone.text)}>
          {pct == null ? "—" : `${pct}%`}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", tone.bar)}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
}

export function ConfidenceRing({ value, size = 88 }: { value: number | null; size?: number }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  const tone = toneForValue(pct);
  const strokeWidth = 7;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct / 100);

  const strokeColor =
    tone.bar === "bg-success" ? "hsl(var(--success))" : tone.bar === "bg-warning" ? "hsl(var(--warning))" : "hsl(var(--danger))";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="hsl(var(--muted))" strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold tabular-nums">{value == null ? "—" : `${pct}%`}</span>
      </div>
    </div>
  );
}

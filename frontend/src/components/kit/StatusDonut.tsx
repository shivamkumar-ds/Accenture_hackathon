const SEGMENT_COLOR: Record<string, string> = {
  met: "hsl(var(--success))",
  conditional: "hsl(var(--warning))",
  review_required: "hsl(var(--info))",
  not_met: "hsl(var(--danger))",
};

export function StatusDonut({
  segments,
  size = 120,
  centerLabel,
}: {
  segments: { key: string; label: string; count: number }[];
  size?: number;
  centerLabel: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.count, 0) || 1;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let offsetSoFar = 0;
  const arcs = segments
    .filter((s) => s.count > 0)
    .map((s) => {
      const fraction = s.count / total;
      const dash = fraction * circumference;
      const arc = (
        <circle
          key={s.key}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={SEGMENT_COLOR[s.key] ?? "hsl(var(--muted-foreground))"}
          strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={-offsetSoFar}
          strokeLinecap="butt"
        />
      );
      offsetSoFar += dash;
      return arc;
    });

  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} stroke="hsl(var(--muted))" strokeWidth={strokeWidth} fill="none" />
          {arcs}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold tabular-nums">{centerLabel}</span>
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Average</span>
        </div>
      </div>
      <div className="space-y-2 min-w-0">
        {segments.map((s) => (
          <div key={s.key} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: SEGMENT_COLOR[s.key] ?? "hsl(var(--muted-foreground))" }} />
            <span className="text-muted-foreground truncate">{s.label}</span>
            <span className="font-semibold tabular-nums shrink-0">
              {total ? Math.round((s.count / total) * 100) : 0}% ({s.count})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

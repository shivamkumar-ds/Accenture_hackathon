import { useEffect, useState } from "react";
import { Clock3 } from "lucide-react";
import { cn } from "../../lib/cn";

/**
 * Ticks off the client's own clock -- no backend endpoint needed, it's
 * just Date(). Shared across Layout (topbar) and Documents (freshness
 * stamp) so "add a live clock" only had to be solved once, in one place.
 * 12-hour format with AM/PM per the brand brief; updates once a minute
 * (not every second) -- a ticking second-hand in a persistent header reads
 * restless for an enterprise product, a calm minute-tick is enough to
 * prove it's live without drawing the eye every second.
 */
export function LiveClock({
  className,
  showDate = true,
  stacked = false,
}: {
  className?: string;
  showDate?: boolean;
  stacked?: boolean;
}) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  const time = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  const date = now.toLocaleDateString([], { weekday: "short", day: "2-digit", month: "short", year: "numeric" });

  if (stacked) {
    return (
      <div className={cn("flex items-start gap-2", className)}>
        <Clock3 size={15} className="text-muted-foreground mt-0.5" />
        <div className="leading-tight">
          <p className="font-semibold tabular-nums">{time}</p>
          {showDate && <p className="text-xs text-muted-foreground tabular-nums">{date}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-1.5 tabular-nums", className)}>
      <span className="font-medium">{time}</span>
      {showDate && <span className="text-muted-foreground font-normal">· {date}</span>}
    </div>
  );
}

function computeGreeting(name?: string) {
  const h = new Date().getHours();
  const label = h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : h < 21 ? "Good evening" : "Working late";
  return name ? `${label}, ${name.split(" ")[0]}` : label;
}

export function useGreeting(name?: string) {
  const [greeting, setGreeting] = useState(() => computeGreeting(name));
  useEffect(() => {
    const id = setInterval(() => setGreeting(computeGreeting(name)), 60_000);
    return () => clearInterval(id);
  }, [name]);
  return greeting;
}

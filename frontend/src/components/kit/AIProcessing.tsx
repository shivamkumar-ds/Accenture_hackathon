import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

/**
 * The processing moment for a real, synchronous LLM call (Capability
 * Builder, Tender Analyzer, Decision Engine can all take real seconds).
 * Cycles through stage labels on a timer -- not tied to real backend
 * progress (the API gives none), but honest about that: it communicates
 * "something intelligent is happening," not a fake progress percentage.
 */
export function AIProcessing({ stages, className = "" }: { stages: string[]; className?: string }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((i) => (i < stages.length - 1 ? i + 1 : i));
    }, 1800);
    return () => clearInterval(interval);
  }, [stages.length]);

  return (
    <div className={`flex flex-col items-center justify-center text-center py-12 px-6 ${className}`}>
      <div className="relative w-14 h-14 mb-5">
        <div className="absolute inset-0 rounded-full bg-primary/15 animate-ping" />
        <div className="relative w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
          <Sparkles size={22} className="text-primary" />
        </div>
      </div>
      <p className="text-sm font-medium">{stages[index]}</p>
      <p className="text-xs text-muted-foreground mt-1">This runs a real AI model call — usually a few seconds.</p>
      <div className="flex gap-1.5 mt-4">
        {stages.map((_, i) => (
          <span
            key={i}
            className={`h-1 rounded-full transition-all duration-500 ${
              i <= index ? "w-6 bg-primary" : "w-2 bg-muted"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

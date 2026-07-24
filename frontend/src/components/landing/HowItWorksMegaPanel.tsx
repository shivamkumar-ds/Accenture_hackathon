import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { cn } from "../../lib/cn";
import { howItWorks } from "./landingData";

export function HowItWorksMegaPanel() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div>
      <div className="mb-8">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
          <Sparkles size={12} />
          From upload to decision
        </span>
        <h2 className="mt-4 text-2xl lg:text-3xl font-bold tracking-tight leading-[1.1] text-foreground lg:whitespace-nowrap">
          How BidOps AI Reaches a Decision
        </h2>
        <p className="mt-3 text-sm text-muted-foreground leading-relaxed max-w-lg">
          Every step is transparent and evidence-backed — from the first document you upload to the final GO / NO-GO
          call.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {howItWorks.map((card, i) => {
          const isOpen = expanded === i;
          return (
            <div
              key={card.title}
              className="rounded-xl border border-border bg-surface p-4 transition-shadow hover:shadow-elevated"
            >
              <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-3">
                <card.icon size={17} />
              </div>
              <p className="text-sm font-semibold tracking-tight leading-snug">{card.title}</p>
              <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{card.description}</p>
              <button
                onClick={() => setExpanded(isOpen ? null : i)}
                className="text-xs font-semibold text-primary mt-3 inline-flex items-center gap-1 hover:underline"
                aria-expanded={isOpen}
              >
                Learn more
                <ArrowRight size={12} className={cn("transition-transform", isOpen && "translate-x-0.5")} />
              </button>
              {isOpen && (
                <ul className="mt-3 pt-3 border-t border-border space-y-1.5 animate-fade-in">
                  {card.details.map((d) => (
                    <li key={d} className="text-xs text-muted-foreground leading-relaxed flex gap-2">
                      <span className="text-primary shrink-0">•</span>
                      {d}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

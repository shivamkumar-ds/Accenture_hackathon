import { useState } from "react";
import { ArrowRight, FileSpreadsheet, FileText, Sparkles } from "lucide-react";
import { cn } from "../../lib/cn";
import { solutionVerticals } from "./landingData";

const DEMO_MAILTO = "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Demo request — BidOps AI");

// Simplified stand-in for the reference image's "documents flowing into
// a dashboard" illustration -- three color-coded file chips next to a
// small dashboard preview, not a literal traced reproduction of the
// dashed-connector artwork (same "faithful in spirit, not pixel-traced"
// approach already used for the hero's DashboardPreview mock).
function DocumentsToDashboardArt() {
  return (
    <div className="hidden lg:flex items-center justify-center gap-6 relative">
      <div className="flex flex-col gap-3">
        <div className="w-11 h-11 rounded-xl bg-danger-soft border border-danger/20 flex items-center justify-center rotate-[-6deg] shadow-xs">
          <FileText size={18} className="text-danger" />
        </div>
        <div className="w-11 h-11 rounded-xl bg-info-soft border border-info/20 flex items-center justify-center rotate-[4deg] shadow-xs ml-4">
          <FileText size={18} className="text-info" />
        </div>
        <div className="w-11 h-11 rounded-xl bg-success-soft border border-success/20 flex items-center justify-center rotate-[-3deg] shadow-xs">
          <FileSpreadsheet size={18} className="text-success" />
        </div>
      </div>

      <div className="w-52 rounded-xl border border-border bg-surface shadow-elevated p-3">
        <div className="flex items-center gap-1 mb-2.5">
          <span className="w-1.5 h-1.5 rounded-full bg-danger/40" />
          <span className="w-1.5 h-1.5 rounded-full bg-warning/40" />
          <span className="w-1.5 h-1.5 rounded-full bg-success/40" />
        </div>
        <div className="h-2 w-2/3 rounded bg-muted mb-3" />
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-muted h-10 flex items-center justify-center">
            <div className="w-6 h-6 rounded-full border-4 border-primary/25 border-t-primary" />
          </div>
          <div className="rounded-lg bg-muted h-10 flex items-end gap-0.5 px-2 pb-1.5">
            <span className="w-1.5 h-3 bg-primary/40 rounded-sm" />
            <span className="w-1.5 h-5 bg-primary/60 rounded-sm" />
            <span className="w-1.5 h-4 bg-primary/50 rounded-sm" />
            <span className="w-1.5 h-6 bg-primary rounded-sm" />
          </div>
        </div>
      </div>
    </div>
  );
}

export function SolutionsMegaPanel() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div>
      <div className="grid lg:grid-cols-[1fr_auto] gap-8 items-center mb-8">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
            <Sparkles size={12} />
            Solutions built for every procurement need
          </span>
          <h2 className="mt-4 text-3xl font-bold tracking-tight leading-[1.1] text-foreground">
            Solutions That Fit
            <br />
            the Way You Work
          </h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed max-w-lg">
            BidOps AI adapts to your industry, your team size, and your procurement complexity — helping you
            evaluate tenders with clarity and confidence.
          </p>
        </div>

        <DocumentsToDashboardArt />
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {solutionVerticals.map((card, i) => {
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

      <div className="mt-4 rounded-xl bg-primary/5 border border-primary/15 px-5 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Sparkles size={15} />
          </div>
          <p className="text-sm text-foreground">
            <span className="font-semibold">Not sure where you fit?</span>{" "}
            <span className="text-muted-foreground">BidOps AI is flexible and adapts to your unique procurement process.</span>
          </p>
        </div>
        <a
          href={DEMO_MAILTO}
          className="text-sm font-semibold text-primary inline-flex items-center gap-1 hover:underline shrink-0"
        >
          Talk to our experts
          <ArrowRight size={14} />
        </a>
      </div>
    </div>
  );
}

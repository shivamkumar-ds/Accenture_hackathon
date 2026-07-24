import { useMemo, useState } from "react";
import { ArrowRight, CalendarDays, Play, Sparkles } from "lucide-react";
import { Button } from "../kit";
import { cn } from "../../lib/cn";
import { featureCategories, featureHighlights, features } from "./landingData";

const DEMO_MAILTO = "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Demo request — BidOps AI");

export function FeaturesMegaPanel() {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [activeCategory, setActiveCategory] = useState<(typeof featureCategories)[number]>("All Features");

  const visibleCards = useMemo(
    () => (activeCategory === "All Features" ? features : features.filter((c) => c.category === activeCategory)),
    [activeCategory]
  );

  return (
    <div>
      {/* Intro row: heading/copy on the left, capability highlights on the right */}
      <div className="grid lg:grid-cols-[1.2fr_1fr] gap-8 items-center mb-10">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
            <Sparkles size={12} />
            Powerful features, purpose-built for procurement
          </span>
          <h2 className="mt-4 text-2xl lg:text-3xl font-bold tracking-tight leading-[1.1] text-foreground">
            Everything You Need to Win More Tenders.
          </h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed max-w-lg">
            BidOps AI brings together document intelligence, capability management, compliance automation, and
            decision intelligence in a single platform designed for modern procurement teams.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface grid grid-cols-2 divide-x divide-y divide-border overflow-hidden">
          {featureHighlights.map((h) => (
            <div key={h.title} className="p-4">
              <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-2.5">
                <h.icon size={16} />
              </div>
              <p className="text-xs font-semibold tracking-tight leading-snug">{h.title}</p>
              <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{h.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Core features + category filter */}
      <div className="text-center mb-6">
        <h3 className="text-lg font-bold tracking-tight text-foreground">Our Core Features</h3>
        <p className="mt-1.5 text-sm text-muted-foreground">
          A complete suite of AI-powered tools to streamline your tender lifecycle.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2 mb-6">
        {featureCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors border",
              activeCategory === cat
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-surface text-foreground/70 border-border hover:bg-surface-hover"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {visibleCards.map((card, i) => {
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

      {/* Bottom banner -- decorative mockup + copy + CTA, no "talk to an
          expert" line here (explicitly not wanted for this panel). */}
      <div className="mt-8 rounded-xl border border-primary/15 bg-primary/5 px-6 py-5 flex flex-col sm:flex-row items-center gap-6">
        <div className="w-24 h-16 rounded-lg bg-surface border border-border shrink-0 flex items-center justify-center relative overflow-hidden">
          <span className="absolute top-1.5 left-1.5 flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-muted" />
            <span className="w-1.5 h-1.5 rounded-full bg-muted" />
            <span className="w-1.5 h-1.5 rounded-full bg-muted" />
          </span>
          <div className="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center">
            <Play size={12} fill="currentColor" />
          </div>
        </div>

        <div className="flex-1 text-center sm:text-left">
          <p className="text-sm font-semibold text-foreground">Built for Procurement Teams of All Sizes</p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            From small businesses to large enterprises, BidOps AI adapts to your workflow and helps you make
            confident, data-backed decisions.
          </p>
        </div>

        <Button size="md" icon={<CalendarDays size={14} />} onClick={() => (window.location.href = DEMO_MAILTO)} className="shrink-0">
          Book A Demo
        </Button>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, ChevronDown, KeyRound, Menu as MenuIcon, X } from "lucide-react";
import { Button, Logo } from "../kit";
import { cn } from "../../lib/cn";
import { features, howItWorks, type DropdownCard } from "./landingData";
import { SolutionsMegaPanel } from "./SolutionsMegaPanel";

// Trimmed down per explicit founder direction: only Solutions, Features,
// How It Works, Pricing, Contact -- Industries, Resources, and About
// (previously in the nav) are gone. The data arrays for Industries/
// Resources still exist in landingData.ts in case they come back later,
// they're just not imported/rendered here anymore.
type DropdownKey = "solutions" | "features" | "how-it-works";

const DROPDOWN_ITEMS: { key: DropdownKey; label: string }[] = [
  { key: "solutions", label: "Solutions" },
  { key: "features", label: "Features" },
  { key: "how-it-works", label: "How It Works" },
];

const DEMO_MAILTO =
  "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Demo request — BidOps AI");

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function CardGrid({ cards }: { cards: DropdownCard[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((card, i) => {
        const isOpen = expanded === i;
        return (
          <div key={card.title} className="rounded-xl border border-border bg-surface p-4 transition-shadow hover:shadow-elevated">
            <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-3">
              <card.icon size={16} />
            </div>
            <p className="text-sm font-semibold tracking-tight">{card.title}</p>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{card.description}</p>
            <button
              onClick={() => setExpanded(isOpen ? null : i)}
              className="text-xs font-medium text-primary mt-2.5 inline-flex items-center gap-1 hover:underline"
              aria-expanded={isOpen}
            >
              Learn More
              <ChevronDown size={12} className={cn("transition-transform", isOpen && "rotate-180")} />
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
  );
}

function MenuPanel({ activeKey }: { activeKey: DropdownKey }) {
  if (activeKey === "solutions") {
    return <SolutionsMegaPanel />;
  }

  if (activeKey === "features") {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Features</p>
        <CardGrid cards={features} />
      </div>
    );
  }

  // how-it-works
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">How It Works</p>
      <CardGrid cards={howItWorks} />
    </div>
  );
}

export function LandingNavbar() {
  const [activeKey, setActiveKey] = useState<DropdownKey | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setActiveKey(null);
    }
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setActiveKey(null);
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onClickOutside);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onClickOutside);
    };
  }, []);

  function toggle(key: DropdownKey) {
    setActiveKey((cur) => (cur === key ? null : key));
  }

  return (
    <div ref={rootRef} className="sticky top-0 z-50 bg-background/90 backdrop-blur border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex flex-col shrink-0" onClick={() => setActiveKey(null)}>
          <Logo size={24} wordmarkClassName="text-[15px]" />
          <span className="text-[10px] text-muted-foreground pl-8 -mt-0.5">From Documents to Decisions.</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-1" aria-label="Primary">
          {DROPDOWN_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => toggle(item.key)}
              className={cn(
                "flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                activeKey === item.key
                  ? "text-primary bg-primary/10"
                  : "text-foreground/80 hover:text-foreground hover:bg-surface-hover"
              )}
              aria-expanded={activeKey === item.key}
            >
              {item.label}
              <ChevronDown size={13} className={cn("transition-transform", activeKey === item.key && "rotate-180")} />
            </button>
          ))}
          <button
            onClick={() => {
              setActiveKey(null);
              scrollToId("pricing");
            }}
            className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-surface-hover"
          >
            Pricing
          </button>
          <button
            onClick={() => {
              setActiveKey(null);
              scrollToId("contact");
            }}
            className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-surface-hover"
          >
            Contact
          </button>
        </nav>

        <div className="hidden lg:flex items-center gap-2.5 shrink-0">
          <Link to="/login">
            <Button variant="outline" size="md" icon={<KeyRound size={14} />}>
              Login
              <ChevronDown size={12} className="text-muted-foreground" />
            </Button>
          </Link>
          <Button size="md" icon={<CalendarDays size={14} />} onClick={() => (window.location.href = DEMO_MAILTO)}>
            Book A Demo
          </Button>
        </div>

        <button
          className="lg:hidden text-foreground"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
        >
          {mobileOpen ? <X size={20} /> : <MenuIcon size={20} />}
        </button>
      </div>

      {activeKey && (
        <div className="hidden lg:block border-t border-border bg-background animate-fade-in">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <MenuPanel activeKey={activeKey} />
          </div>
        </div>
      )}

      {mobileOpen && (
        <div className="lg:hidden border-t border-border bg-background px-4 py-4 space-y-1 animate-fade-in">
          {DROPDOWN_ITEMS.map((item) => (
            <div key={item.key}>
              <button
                onClick={() => toggle(item.key)}
                className="w-full flex items-center justify-between rounded-md px-3 py-2.5 text-sm font-medium text-foreground/90"
              >
                {item.label}
                <ChevronDown size={14} className={cn("transition-transform", activeKey === item.key && "rotate-180")} />
              </button>
              {activeKey === item.key && (
                <div className="px-3 pb-3">
                  <MenuPanel activeKey={item.key} />
                </div>
              )}
            </div>
          ))}
          <button
            onClick={() => {
              scrollToId("pricing");
              setMobileOpen(false);
            }}
            className="w-full text-left rounded-md px-3 py-2.5 text-sm font-medium text-foreground/90"
          >
            Pricing
          </button>
          <button
            onClick={() => {
              scrollToId("contact");
              setMobileOpen(false);
            }}
            className="w-full text-left rounded-md px-3 py-2.5 text-sm font-medium text-foreground/90"
          >
            Contact
          </button>
          <div className="flex items-center gap-2.5 pt-3">
            <Link to="/login" className="flex-1">
              <Button variant="outline" size="md" className="w-full">
                Login
              </Button>
            </Link>
            <Button size="md" className="flex-1" onClick={() => (window.location.href = DEMO_MAILTO)}>
              Book A Demo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

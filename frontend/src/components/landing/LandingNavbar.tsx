import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Menu as MenuIcon, X } from "lucide-react";
import { Button, Logo } from "../kit";
import { cn } from "../../lib/cn";
import { solutions, features, industries, resources, type DropdownCard } from "./landingData";

type MenuKey = "solutions" | "features" | "industries" | "resources" | "pricing";

const NAV_ITEMS: { key: MenuKey; label: string }[] = [
  { key: "solutions", label: "Solutions" },
  { key: "features", label: "Features" },
  { key: "industries", label: "Industries" },
  { key: "resources", label: "Resources" },
  { key: "pricing", label: "Pricing" },
];

const DEMO_MAILTO =
  "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Demo request — BidOps AI");
const SALES_MAILTO =
  "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Sales enquiry — BidOps AI");

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function CardGrid({ cards }: { cards: DropdownCard[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="grid sm:grid-cols-2 gap-3">
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

function MenuPanel({ activeKey }: { activeKey: MenuKey }) {
  if (activeKey === "solutions") {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Solutions</p>
        <CardGrid cards={solutions} />
      </div>
    );
  }

  if (activeKey === "features") {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Features</p>
        <CardGrid cards={features} />
      </div>
    );
  }

  if (activeKey === "industries") {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Industries</p>
        <div className="grid sm:grid-cols-3 gap-3">
          {industries.map((ind) => (
            <div key={ind.name} className="rounded-xl border border-border bg-surface p-4 flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-brand-accent/10 text-brand-accent flex items-center justify-center shrink-0">
                <ind.icon size={16} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-tight">{ind.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{ind.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeKey === "resources") {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Resources</p>
        <div className="grid sm:grid-cols-3 gap-3">
          {resources.map((r) => (
            <div key={r.title} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <r.icon size={16} />
                </div>
                <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                  Coming soon
                </span>
              </div>
              <p className="text-sm font-semibold tracking-tight">{r.title}</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{r.description}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // pricing
  return (
    <div className="max-w-xl">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Pricing</p>
      <p className="text-sm text-foreground leading-relaxed">
        Pricing plans are currently being finalized. We're working closely with our early design partners to build
        pricing that scales with organizations of every size.
      </p>
      <div className="flex flex-wrap gap-3 mt-4">
        <Button size="md" onClick={() => (window.location.href = DEMO_MAILTO)}>
          Request a Demo
        </Button>
        <Button variant="outline" size="md" onClick={() => (window.location.href = SALES_MAILTO)}>
          Contact Sales
        </Button>
      </div>
    </div>
  );
}

export function LandingNavbar() {
  const [activeKey, setActiveKey] = useState<MenuKey | null>(null);
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

  function toggle(key: MenuKey) {
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
          {NAV_ITEMS.map((item) => (
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
            onClick={() => scrollToId("company")}
            className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-surface-hover"
          >
            About
          </button>
          <button
            onClick={() => scrollToId("contact")}
            className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-surface-hover"
          >
            Contact
          </button>
        </nav>

        <div className="hidden lg:flex items-center gap-2.5 shrink-0">
          <Link to="/login">
            <Button variant="outline" size="md">
              Login
            </Button>
          </Link>
          <Button size="md" onClick={() => (window.location.href = DEMO_MAILTO)}>
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
          {NAV_ITEMS.map((item) => (
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
              scrollToId("company");
              setMobileOpen(false);
            }}
            className="w-full text-left rounded-md px-3 py-2.5 text-sm font-medium text-foreground/90"
          >
            About
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

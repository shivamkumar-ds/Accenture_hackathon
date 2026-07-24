import { Link } from "react-router-dom";
import { ArrowRight, FileSearch, Layers, ShieldCheck, FileBarChart2 } from "lucide-react";
import { Button, Logo } from "../components/kit";
import { LandingNavbar } from "../components/landing/LandingNavbar";
import { DashboardPreview } from "../components/landing/DashboardPreview";
import { trustStatements } from "../components/landing/landingData";

const DEMO_MAILTO = "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Demo request — BidOps AI");
const SALES_MAILTO = "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Sales enquiry — BidOps AI");

const pills = [
  { icon: FileSearch, title: "AI Requirement Extraction", description: "Automatically extract tender requirements using AI." },
  { icon: Layers, title: "Capability Intelligence", description: "Build a reusable capability library from company documents." },
  { icon: ShieldCheck, title: "Evidence-backed Decisions", description: "Every recommendation links directly to supporting evidence." },
  { icon: FileBarChart2, title: "Executive Reports", description: "Generate procurement-ready decision reports in minutes." },
];

const footerLinks = {
  Company: [{ label: "About", id: "company" }, { label: "Contact", id: "contact" }],
  Product: [{ label: "Solutions" }, { label: "Features" }, { label: "Industries" }],
  Resources: [{ label: "Documentation" }, { label: "FAQ" }, { label: "Release Notes" }],
};

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <LandingNavbar />

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Soft blue gradient wash, not a hard block -- keeps the premium
            "white background, subtle depth" feel from the brief rather
            than a saturated hero banner. */}
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,hsl(var(--primary)/0.10),transparent)]"
        />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-10 lg:pt-10 lg:pb-12 grid lg:grid-cols-2 gap-10 items-start">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              AI-Powered Procurement Intelligence
            </span>

            <h1 className="mt-4 text-4xl sm:text-5xl lg:text-[3.3rem] font-bold tracking-tight leading-[1.06] text-foreground">
              From Documents
              <br />
              to Decisions.
              <br />
              <span className="text-primary">Organize. Analyze. Automate.</span>
            </h1>

            <p className="mt-4 text-base text-muted-foreground leading-relaxed max-w-xl">
              BidOps AI helps procurement teams analyze tender documents, build organizational capabilities, evaluate
              compliance, and generate explainable bid recommendations — all from a single enterprise workspace.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={() => (window.location.href = DEMO_MAILTO)} icon={<ArrowRight size={16} />}>
                Book a Demo
              </Button>
              <Button variant="outline" size="lg" onClick={() => scrollToId("features-anchor")}>
                Explore Features
              </Button>
            </div>

            <p className="mt-4 text-xs text-muted-foreground flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>Enterprise-Grade Security</span>
              <span aria-hidden="true">•</span>
              <span>Explainable AI Decisions</span>
              <span aria-hidden="true">•</span>
              <span>Built for Procurement Teams</span>
            </p>
          </div>

          {/* Sticky so the mockup stays pinned near the top of the
              viewport while the (taller) left column scrolls past it,
              instead of ending early and leaving a block of empty white
              space beneath a short card -- the actual bug being fixed
              here, not just cosmetic centering. */}
          <div className="lg:sticky lg:top-24">
            <DashboardPreview />
          </div>

          {/* Full-width row, not confined to the half-width left column --
              spreading these horizontally across the whole page uses the
              space properly instead of a cramped 2x2 grid with empty
              space beside it. */}
          <div className="lg:col-span-2 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {pills.map((pill) => (
              <div key={pill.title} className="flex items-start gap-3 rounded-xl border border-border bg-surface p-3.5 shadow-xs transition-shadow hover:shadow-elevated">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <pill.icon size={15} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold tracking-tight">{pill.title}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{pill.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust row -- capability statements only, no fabricated metrics
          or customer logos (explicit constraint). */}
      <section id="features-anchor" className="border-y border-border bg-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-7">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-6">
            {trustStatements.map((t) => (
              <div key={t.label} className="flex flex-col items-center text-center gap-2">
                <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                  <t.icon size={17} />
                </div>
                <p className="text-xs font-medium text-foreground/80 leading-snug">{t.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing -- no invented numbers, honest "still finalizing" copy. */}
      <section id="pricing" className="bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 text-center">
          <h2 className="text-2xl font-bold tracking-tight">Pricing</h2>
          <p className="mt-3 text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Pricing plans are currently being finalized. We're working closely with our early design partners to
            build pricing that scales with organizations of every size.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
            <Button size="md" onClick={() => (window.location.href = DEMO_MAILTO)}>
              Request a Demo
            </Button>
            <Button variant="outline" size="md" onClick={() => (window.location.href = SALES_MAILTO)}>
              Contact Sales
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="company" className="bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10">
            <div>
              <Logo size={22} />
              <p className="text-sm text-muted-foreground mt-3 leading-relaxed max-w-xs">
                BidOps AI is the end-to-end platform that helps procurement teams discover the right tenders, analyze
                complex documents, build capabilities, and generate compliant bids with confidence.
              </p>
            </div>

            {Object.entries(footerLinks).map(([heading, links]) => (
              <div key={heading}>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">{heading}</p>
                <ul className="space-y-2">
                  {links.map((link) => (
                    <li key={link.label}>
                      {"id" in link && link.id ? (
                        <button
                          onClick={() => scrollToId(link.id!)}
                          className="text-sm text-foreground/75 hover:text-primary transition-colors"
                        >
                          {link.label}
                        </button>
                      ) : (
                        <span className="text-sm text-foreground/75">{link.label}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            <div id="contact">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Contact</p>
              <a href={DEMO_MAILTO} className="text-sm text-foreground/75 hover:text-primary transition-colors block">
                bidops.ai@gmail.com
              </a>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => (window.location.href = SALES_MAILTO)}
              >
                Contact Sales
              </Button>
            </div>
          </div>

          <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">© 2026 BidOps AI. All rights reserved.</p>
            <div className="flex items-center gap-5">
              <span className="text-xs text-muted-foreground">Privacy Policy</span>
              <span className="text-xs text-muted-foreground">Terms</span>
              <span className="text-xs text-muted-foreground">Security</span>
              <Link to="/login" className="text-xs font-medium text-primary hover:underline">
                Login
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

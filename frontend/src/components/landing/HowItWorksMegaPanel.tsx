import { CheckCircle2, FileUp, Sparkles } from "lucide-react";
import { cn } from "../../lib/cn";
import { processSteps, processTrustPoints } from "./landingData";

function PreviewCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3 text-left min-w-0">
      <p className="text-[10px] font-semibold text-foreground/90 mb-2 truncate">{title}</p>
      {children}
    </div>
  );
}

function PdfBadge() {
  return <span className="text-[8px] font-semibold text-danger bg-danger-soft rounded px-1 py-0.5 shrink-0">PDF</span>;
}

export function HowItWorksMegaPanel() {
  return (
    <div>
      <div className="text-center mb-8">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
          <Sparkles size={12} />
          Our Process
        </span>
        <h2 className="mt-4 text-2xl lg:text-3xl font-bold tracking-tight leading-[1.1] text-foreground">
          From Documents to Decisions
        </h2>
        <p className="mt-3 text-sm text-muted-foreground leading-relaxed max-w-xl mx-auto">
          BidOps AI follows a proven, AI-powered workflow to evaluate tenders, assess your capabilities, and deliver
          clear, evidence-backed recommendations.
        </p>
      </div>

      {/* 7-step timeline */}
      <div className="relative mb-6">
        <div className="hidden lg:block absolute top-[22px] left-[7%] right-[7%] border-t-2 border-dashed border-border" />
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-x-3 gap-y-6 relative">
          {processSteps.map((s) => (
            <div key={s.step} className="flex flex-col items-center text-center">
              <div className="w-11 h-11 rounded-full bg-background border-2 border-primary/25 text-primary font-bold flex items-center justify-center text-sm mb-3 relative z-10">
                {s.step}
              </div>
              <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center mb-3", s.color.bg, s.color.text)}>
                <s.icon size={19} />
              </div>
              <p className="text-xs font-semibold tracking-tight leading-snug">{s.title}</p>
              <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{s.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Realistic (illustrative, not live) preview of each step's screen */}
      <div className="hidden lg:grid grid-cols-7 gap-3 mb-8">
        <PreviewCard title="My Documents">
          <div className="space-y-1.5">
            {["ISO 9001 Certificate.pdf", "Company Profile.pdf", "Work Orders.pdf", "Financial Statement.pdf"].map((f) => (
              <div key={f} className="flex items-center gap-1.5 text-[9px] text-foreground/80">
                <FileUp size={10} className="text-primary shrink-0" />
                <span className="truncate flex-1">{f}</span>
                <PdfBadge />
              </div>
            ))}
            <div className="mt-2 rounded-md border border-dashed border-border text-center py-1.5 text-[9px] text-muted-foreground">
              Upload more documents
            </div>
          </div>
        </PreviewCard>

        <PreviewCard title="Capability Library">
          <div className="space-y-1.5">
            {[
              ["Certifications", 24],
              ["Past Projects", 18],
              ["Work Orders", 32],
              ["Personnel", 125],
              ["Equipment", 46],
              ["Financials", 12],
            ].map(([label, count]) => (
              <div key={label} className="flex items-center gap-1.5 text-[9px]">
                <CheckCircle2 size={10} className="text-success shrink-0" />
                <span className="text-foreground/80 truncate flex-1">{label}</span>
                <span className="text-muted-foreground font-medium">{count}</span>
              </div>
            ))}
          </div>
        </PreviewCard>

        <PreviewCard title="Tender Document">
          <div className="flex items-center gap-1.5 text-[9px] text-foreground/80 mb-2">
            <FileUp size={10} className="text-violet-600 shrink-0" />
            <span className="truncate flex-1">Tender_12345.pdf</span>
          </div>
          <p className="text-[8px] text-muted-foreground mb-2">8.4 MB</p>
          <div className="rounded-md border border-border bg-background p-2 space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-1 rounded-full bg-muted" style={{ width: `${85 - i * 10}%` }} />
            ))}
          </div>
        </PreviewCard>

        <PreviewCard title="Extracted Requirements">
          <div className="space-y-1.5">
            {[
              ["Technical Requirements", 156],
              ["Financial Requirements", 42],
              ["Eligibility Criteria", 28],
              ["Compliance Clauses", 63],
              ["Commercial Terms", 31],
            ].map(([label, count]) => (
              <div key={label} className="flex items-center justify-between text-[9px]">
                <span className="text-foreground/80 truncate">{label}</span>
                <span className="text-muted-foreground font-medium shrink-0">{count}</span>
              </div>
            ))}
            <div className="flex items-center justify-between text-[9px] font-semibold pt-1.5 mt-1 border-t border-border">
              <span>Total Extracted</span>
              <span className="text-primary">320</span>
            </div>
          </div>
        </PreviewCard>

        <PreviewCard title="Evaluation Summary">
          <div className="relative w-14 h-14 mx-auto mb-2">
            <div
              className="w-14 h-14 rounded-full"
              style={{
                background:
                  "conic-gradient(hsl(var(--success)) 0% 78%, hsl(var(--warning)) 78% 93%, hsl(var(--danger)) 93% 100%)",
              }}
            />
            <div className="absolute inset-[4px] rounded-full bg-surface flex items-center justify-center">
              <span className="text-[10px] font-bold text-success">78%</span>
            </div>
          </div>
          <p className="text-center text-[8px] text-muted-foreground mb-2">Overall Match</p>
          <div className="space-y-1 text-[9px]">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-success shrink-0" />
              <span className="text-foreground/80 flex-1">Matched</span>
              <span className="text-muted-foreground">78%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-warning shrink-0" />
              <span className="text-foreground/80 flex-1">Partial</span>
              <span className="text-muted-foreground">15%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-danger shrink-0" />
              <span className="text-foreground/80 flex-1">Missing</span>
              <span className="text-muted-foreground">7%</span>
            </div>
          </div>
        </PreviewCard>

        <PreviewCard title="Top Gaps">
          <div className="space-y-1.5 mb-2">
            {[
              ["ISO 14001 Certificate", "High", "text-danger bg-danger-soft"],
              ["Average Annual Turnover", "Medium", "text-warning bg-warning-soft"],
              ["Similar Project Experience", "Low", "text-muted-foreground bg-muted"],
            ].map(([label, risk, cls]) => (
              <div key={label} className="flex items-center justify-between gap-1 text-[9px]">
                <span className="text-foreground/80 truncate">{label}</span>
                <span className={cn("text-[8px] font-medium rounded px-1 py-0.5 shrink-0", cls)}>{risk}</span>
              </div>
            ))}
          </div>
          <p className="text-[9px] font-medium text-primary">View all gaps →</p>
        </PreviewCard>

        <PreviewCard title="Recommendation">
          <div className="rounded-md bg-success-soft py-2.5 text-center mb-2">
            <p className="text-lg font-bold text-success leading-none">GO</p>
            <p className="text-[8px] text-success/80 mt-1">High Probability of Success</p>
          </div>
          <div className="space-y-1 text-[9px] font-medium text-primary">
            <p>View Full Report</p>
            <p>Export PDF</p>
          </div>
        </PreviewCard>
      </div>

      {/* Trust row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 pt-6 border-t border-border">
        {processTrustPoints.map((t) => (
          <div key={t.title} className="flex items-start gap-2.5">
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <t.icon size={14} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-foreground">{t.title}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{t.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

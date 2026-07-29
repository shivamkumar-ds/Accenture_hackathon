import { AlertTriangle, Bell, CheckCircle2, ClipboardList, LayoutDashboard, Search, XCircle } from "lucide-react";
import { Logo } from "../kit";

// A static, illustrative mock of the authenticated dashboard -- used only
// in the marketing hero to communicate "this is a real product," not a
// live data view. Deliberately restrained: no invented analytics, no
// exaggerated charts, just the shape of the actual app (sidebar, a
// handful of stat cards, two short lists). Content is representative
// sample data, clearly not a real customer's tenders.
export function DashboardPreview() {
  return (
    <div className="hidden lg:block rounded-2xl border border-border bg-surface shadow-hero overflow-hidden">
      <div className="flex">
        <div className="w-40 shrink-0 border-r border-border bg-background/60 px-3 py-4">
          <div className="mb-4">
            <Logo size={18} wordmarkClassName="text-xs" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 rounded-md bg-primary/10 text-primary px-2.5 py-1.5 text-[11px] font-medium">
              <LayoutDashboard size={12} /> Dashboard
            </div>
            {["Documents", "Capabilities", "Upload Tender", "Tender Workspace"].map((label) => (
              <div key={label} className="rounded-md px-2.5 py-1.5 text-[11px] text-muted-foreground">
                {label}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 min-w-0 flex flex-col">
          <div className="h-10 border-b border-border flex items-center justify-end gap-3 px-4 shrink-0">
            <Search size={12} className="text-muted-foreground" />
            <Bell size={12} className="text-muted-foreground" />
            <div className="w-5 h-5 rounded-full bg-primary/15 text-primary flex items-center justify-center text-[9px] font-semibold">
              A
            </div>
          </div>

          <div className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold tracking-tight">Good morning</p>
              <p className="text-[11px] text-muted-foreground">Here's what needs attention today.</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2.5 mb-4">
            {[
              { label: "Active Assessments", value: "5" },
              { label: "Pending Approvals", value: "2" },
              { label: "Critical Gaps", value: "7", tone: "text-danger" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border border-border bg-surface px-3 py-2.5">
                <p className="text-[9px] font-medium uppercase tracking-wide text-muted-foreground">{stat.label}</p>
                <p className={`text-lg font-semibold tabular-nums mt-0.5 ${stat.tone ?? ""}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="rounded-lg border border-border bg-surface p-3">
              <p className="text-[10px] font-semibold flex items-center gap-1.5 mb-2">
                <ClipboardList size={11} className="text-muted-foreground" /> Tenders Closing Soon
              </p>
              <div className="space-y-1.5">
                {["Water Treatment Plant", "Highway Package 3"].map((t) => (
                  <div key={t} className="flex items-center justify-between text-[10px]">
                    <span className="text-foreground/80 truncate">{t}</span>
                    <AlertTriangle size={10} className="text-warning shrink-0" />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-surface p-3">
              <p className="text-[10px] font-semibold flex items-center gap-1.5 mb-2">
                <CheckCircle2 size={11} className="text-muted-foreground" /> Recent Assessments
              </p>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-foreground/80 truncate">Electrical Substation Works</span>
                  <span className="text-success font-medium shrink-0">GO</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-foreground/80 truncate">Surveillance Platform</span>
                  <span className="text-danger font-medium shrink-0 flex items-center gap-0.5">
                    <XCircle size={9} /> NO-GO
                  </span>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}

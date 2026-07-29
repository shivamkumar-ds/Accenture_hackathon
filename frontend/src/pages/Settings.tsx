import { useEffect, useState } from "react";
import { getCompany } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Card, CardBody, CardHeader, Skeleton, Switch } from "../components/kit";
import type { CompanyRead } from "../api/types";
import { Building2, Info, Palette } from "lucide-react";

// Settings -- three sections, each backed by something that actually
// exists today. No Security, Notifications, Billing, Integrations, or AI
// preferences: none of those have any backend support yet (no
// password-change endpoint, no notification system, no billing or API
// product, only one working AI provider), so they're not represented
// here at all -- not even as "Coming Soon" placeholders. This page
// describes the product as it exists, not a roadmap.
function OrganizationSection() {
  const { user } = useAuth();
  const [company, setCompany] = useState<CompanyRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.company_id) {
      setLoading(false);
      return;
    }
    getCompany(user.company_id)
      .then(setCompany)
      .finally(() => setLoading(false));
  }, [user?.company_id]);

  // Field/value pairs laid out the way an edit form would be -- so that
  // when a real PATCH /company endpoint exists, this same layout gains
  // input elements instead of being rebuilt. No input, edit button, or
  // "coming soon" copy is rendered now: there is no update endpoint for
  // any role, administrator included, so every role sees the identical
  // read-only view.
  const fields: { label: string; value: string | null | undefined }[] = company
    ? [
        { label: "Name", value: company.name },
        { label: "Industry", value: company.industry },
        { label: "Registration Number", value: company.registration_number },
        { label: "Country", value: company.country },
      ]
    : [];

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Building2 size={15} className="text-muted-foreground" />
            Organization
          </span>
        }
        description="Your company's registered details."
      />
      <CardBody>
        {loading ? (
          <div className="grid sm:grid-cols-2 gap-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : !company ? (
          <p className="text-sm text-muted-foreground">Organization details are unavailable.</p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-5">
            {fields.map((f) => (
              <div key={f.label}>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">{f.label}</p>
                <p className="text-sm font-medium">{f.value ?? "—"}</p>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function AppearanceSection() {
  const { theme, toggleTheme } = useTheme();
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Palette size={15} className="text-muted-foreground" />
            Appearance
          </span>
        }
        description="Applies to this browser."
      />
      <CardBody className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium">Dark mode</p>
          <p className="text-xs text-muted-foreground mt-0.5">Currently {theme === "dark" ? "on" : "off"}.</p>
        </div>
        <Switch checked={theme === "dark"} onChange={toggleTheme} label="Toggle dark mode" />
      </CardBody>
    </Card>
  );
}

function AboutSection() {
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Info size={15} className="text-muted-foreground" />
            About
          </span>
        }
      />
      <CardBody className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">BidOps</span>
        <span className="font-medium tabular-nums">v{__APP_VERSION__}</span>
      </CardBody>
    </Card>
  );
}

export default function Settings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Organization details and app preferences.</p>
      </div>

      <div className="space-y-6">
        <AppearanceSection />
        <OrganizationSection />
        <AboutSection />
      </div>
    </div>
  );
}

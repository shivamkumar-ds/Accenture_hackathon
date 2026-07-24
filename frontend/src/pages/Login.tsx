import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login as loginRequest, registerCompany } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Button, Input, Logo } from "../components/kit";
import { ShieldCheck, Gauge, FileSearch } from "lucide-react";

const highlights = [
  { icon: FileSearch, text: "Extracts requirements from tender documents automatically" },
  { icon: Gauge, text: "Matches your capability records against every clause" },
  { icon: ShieldCheck, text: "Generates a GO / NO-GO recommendation with full evidence" },
];

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [companyName, setCompanyName] = useState("");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [industry, setIndustry] = useState("");
  const [country, setCountry] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await loginRequest({ email, password });
      login(res.access_token, res.user);
      navigate("/");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await registerCompany({
        company_name: companyName,
        registration_number: registrationNumber,
        industry: industry || null,
        country: country || null,
        admin_name: adminName,
        admin_email: adminEmail,
        admin_password: adminPassword,
      });
      login(res.access_token, res.user);
      navigate("/");
    } catch (err) {
      notify("error", extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Brand panel -- fixed brand tokens (--brand / --brand-foreground),
          deliberately NOT theme-reactive. This is the actual fix for the
          "white text unreadable" bug: previously this used bg-accent /
          text-accent-foreground (which flip with light/dark mode) while
          children were hardcoded to text-white -- in dark mode the panel
          background flipped light but the text stayed white. A brand/hero
          surface like this should look identical regardless of the
          visitor's OS theme, the same way Stripe/Linear's marketing side
          of a split auth screen never inverts. */}
      <div className="hidden lg:flex flex-col justify-between bg-brand text-brand-foreground p-12 relative overflow-hidden">
        {/* Flat dot-grid texture only -- no blurred glow orbs, per brand
            brief's explicit "no glassmorphism, no neon" rule. */}
        <div className="absolute inset-0 bg-dot-grid opacity-40" />

        <div className="relative">
          <Logo size={30} wordmarkClassName="text-lg text-brand-foreground" />
        </div>

        <div className="relative space-y-8 max-w-md">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-foreground/15 bg-brand-foreground/5 px-3 py-1 text-xs font-medium text-brand-foreground/70">
            Enterprise procurement intelligence
          </span>
          <h1 className="text-4xl font-semibold tracking-tight leading-[1.15] bg-gradient-to-br from-brand-foreground to-brand-foreground/70 bg-clip-text text-transparent">
            From Documents to Decisions.
          </h1>
          <div className="space-y-5">
            {highlights.map((h, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-brand-foreground/10 border border-brand-foreground/10 flex items-center justify-center shrink-0">
                  <h.icon size={16} />
                </div>
                <p className="text-sm text-brand-foreground/75 leading-relaxed pt-2">{h.text}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-brand-foreground/40">© 2026 BidOps. Built for regulated procurement.</p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6 bg-background">
        <div className="w-full max-w-sm animate-fade-in">
          <div className="lg:hidden flex items-center justify-center mb-8">
            <Logo size={24} />
          </div>

          <h2 className="text-xl font-semibold tracking-tight">
            {mode === "login" ? "Welcome back" : "Create your workspace"}
          </h2>
          <p className="text-sm text-muted-foreground mt-1 mb-6">
            {mode === "login" ? "Sign in to continue to your dashboard." : "Register your company to get started."}
          </p>

          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <Input label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
              <Input
                label="Password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <Button type="submit" loading={loading} className="w-full" size="lg">
                Sign in
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-3">
              <Input label="Company Name" required value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
              <Input
                label="Registration Number"
                required
                value={registrationNumber}
                onChange={(e) => setRegistrationNumber(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Industry" value={industry} onChange={(e) => setIndustry(e.target.value)} />
                <Input label="Country" value={country} onChange={(e) => setCountry(e.target.value)} />
              </div>
              <Input label="Admin Name" required value={adminName} onChange={(e) => setAdminName(e.target.value)} />
              <Input
                label="Admin Email"
                type="email"
                required
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
              />
              <Input
                label="Admin Password"
                type="password"
                required
                minLength={8}
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
              />
              <Button type="submit" loading={loading} className="w-full" size="lg">
                Create workspace
              </Button>
            </form>
          )}

          <p className="text-sm text-center text-muted-foreground mt-6">
            {mode === "login" ? "New to BidOps? " : "Already registered? "}
            <button
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-primary font-medium hover:underline"
            >
              {mode === "login" ? "Register your company" : "Sign in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

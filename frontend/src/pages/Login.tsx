import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login as loginRequest, registerCompany } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Button, Input, Logo } from "../components/kit";
import { DashboardPreview } from "../components/landing/DashboardPreview";
import { ArrowLeft, Eye, EyeOff, Lock, Mail, ShieldCheck, Sparkles, Users } from "lucide-react";

const FORGOT_PASSWORD_MAILTO =
  "mailto:bidops.ai@gmail.com?subject=" + encodeURIComponent("Password reset request — BidOps");

// Standard 4-color "G" mark -- lucide-react has no Google logo, so this is
// a small inline SVG rather than pulling in a whole icon-pack dependency.
function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l5.7-5.7C34.6 6 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5Z"
      />
      <path
        fill="#FF3D00"
        d="m6.3 14.7 6.6 4.8C14.6 15.9 18.9 13 24 13c3.1 0 5.8 1.1 8 3l5.7-5.7C34.6 6 29.6 4 24 4c-7.4 0-13.8 4.2-17.1 10.3Z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.5 0 10.4-1.9 14.3-5.1l-6.6-5.6C29.6 34.9 26.9 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.2 39.7 16 44 24 44Z"
      />
      <path
        fill="#1976D2"
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.2 4.2-4 5.6l6.6 5.6C41.6 36 44 30.7 44 24c0-1.3-.1-2.7-.4-3.5Z"
      />
    </svg>
  );
}

// Honest, already-established claims restated as short cards -- no new
// capabilities invented for this page.
const loginHighlights = [
  {
    icon: ShieldCheck,
    color: { bg: "bg-blue-50", text: "text-blue-600" },
    title: "Secure & Private",
    description: "Your data is access-scoped to your company and never shared.",
  },
  {
    icon: Sparkles,
    color: { bg: "bg-emerald-50", text: "text-emerald-600" },
    title: "AI-Powered Insights",
    description: "Extract, match, and evaluate tenders with AI-driven analysis.",
  },
  {
    icon: Users,
    color: { bg: "bg-violet-50", text: "text-violet-600" },
    title: "Built for Procurement Teams",
    description: "Collaborate, analyze, and win more tenders together.",
  },
];

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
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
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/">
            <Logo size={24} />
          </Link>
          <Link
            to="/"
            className="text-sm font-medium text-primary inline-flex items-center gap-1.5 hover:underline"
          >
            <ArrowLeft size={14} />
            Back to Home
          </Link>
        </div>
      </header>

      <div className="flex-1 relative overflow-hidden">
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_60%_50%_at_15%_25%,hsl(var(--primary)/0.08),transparent)]"
        />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-14 grid lg:grid-cols-[1.1fr_1fr] gap-12 items-start">
          {/* Left: pitch + real dashboard preview */}
          <div className="hidden lg:block">
            <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
              {mode === "login" ? "Welcome Back!" : "Get Started"}
            </h1>
            <p className="mt-2 text-base text-muted-foreground">
              {mode === "login" ? "Sign in to your BidOps account" : "Register your company to get started"}
            </p>

            <div className="mt-8 space-y-5">
              {loginHighlights.map((h) => (
                <div key={h.title} className="flex items-start gap-3.5">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${h.color.bg} ${h.color.text}`}>
                    <h.icon size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{h.title}</p>
                    <p className="text-sm text-muted-foreground mt-0.5">{h.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-10 max-w-md">
              <DashboardPreview />
            </div>
          </div>

          {/* Right: auth card */}
          <div className="w-full max-w-md lg:ml-auto">
            <div className="rounded-2xl border border-border bg-surface shadow-elevated p-6 lg:p-8">
              <div className="lg:hidden flex justify-center mb-6">
                <Logo size={22} />
              </div>

              <h2 className="font-display text-2xl font-bold text-center tracking-tight text-foreground">
                {mode === "login" ? "Login" : "Create your workspace"}
              </h2>
              <p className="text-sm text-muted-foreground text-center mt-1 mb-6">
                {mode === "login" ? "Enter your credentials to access your account" : "Register your company to get started."}
              </p>

              {mode === "login" ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <Input
                    label="Email Address"
                    type="email"
                    required
                    icon={Mail}
                    placeholder="Enter your email address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Input
                    label="Password"
                    type={showPassword ? "text" : "password"}
                    required
                    icon={Lock}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    trailing={
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="text-muted-foreground hover:text-foreground"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    }
                  />

                  <div className="flex justify-end">
                    <a href={FORGOT_PASSWORD_MAILTO} className="text-xs font-medium text-primary hover:underline">
                      Forgot Password?
                    </a>
                  </div>

                  <Button type="submit" loading={loading} className="w-full" size="lg">
                    Sign In
                  </Button>

                  <div className="flex items-center gap-3 py-1">
                    <div className="h-px flex-1 bg-border" />
                    <span className="text-xs text-muted-foreground">OR</span>
                    <div className="h-px flex-1 bg-border" />
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    className="w-full"
                    onClick={() => notify("info", "Google sign-in is coming soon.")}
                    icon={<GoogleIcon />}
                  >
                    Sign in with Google
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
      </div>

      <footer className="shrink-0 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-xs text-muted-foreground">© 2026 BidOps. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

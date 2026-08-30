import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import { usePasteSanitizer } from "./lib/usePasteSanitizer";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import ActionCenter from "./pages/ActionCenter";
import Documents from "./pages/Documents";
import Capabilities from "./pages/Capabilities";
import TenderUpload from "./pages/TenderUpload";
import Missions from "./pages/Missions";
import Evaluation from "./pages/Evaluation";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      {/* Accenture demo: the public marketing Landing page is not part
          of this demo and has been removed from routing (not deleted --
          pages/Landing.tsx still exists on disk, just unreferenced).
          Signed-out users at "/" now land directly on Login instead.
          Once authenticated, the second "/" route below (inside
          RequireAuth + Layout) takes over as before -- no authenticated
          route or internal link is touched by this. */}
      {!isAuthenticated && <Route path="/" element={<Navigate to="/login" replace />} />}
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/action-center" element={<ActionCenter />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/capabilities" element={<Capabilities />} />
        <Route path="/tenders/new" element={<TenderUpload />} />
        <Route path="/missions" element={<Missions />} />
        <Route path="/missions/:missionId" element={<Evaluation />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        {/* Reports.tsx retired -- it was a strictly smaller, less capable
            duplicate view over the same list_missions() data Tender
            Workspace already fully contains (Tender Workspace already
            lists every non-archived mission at every status; Reports only
            ever showed the subset with a recommendation_id, with no
            actions beyond Open). Redirected rather than dropped through
            the catch-all so any existing bookmark or external link to
            /reports still lands somewhere useful instead of the
            dashboard. */}
        <Route path="/reports" element={<Navigate to="/missions" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  // App-wide: strips leading/trailing whitespace introduced by pasting
  // clipboard content (very commonly copied out of a tender PDF, which
  // often carries leading whitespace from list indentation) into any text
  // field, anywhere -- see usePasteSanitizer.ts's own docstring.
  usePasteSanitizer();

  return (
    <ThemeProvider>
      <ToastProvider>
        <BrowserRouter>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </ToastProvider>
    </ThemeProvider>
  );
}

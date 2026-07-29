import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Capabilities from "./pages/Capabilities";
import TenderUpload from "./pages/TenderUpload";
import Missions from "./pages/Missions";
import Evaluation from "./pages/Evaluation";
import Reports from "./pages/Reports";

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
      {/* Public marketing landing page -- only reachable at "/" while
          signed out. Once authenticated, the second "/" route below
          (inside RequireAuth + Layout) takes over instead, so this
          doesn't touch any existing authenticated route or internal
          link -- every "/documents", "/tenders/new" etc. link in the
          app is untouched by this. */}
      {!isAuthenticated && <Route path="/" element={<Landing />} />}
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/capabilities" element={<Capabilities />} />
        <Route path="/tenders/new" element={<TenderUpload />} />
        <Route path="/missions" element={<Missions />} />
        <Route path="/missions/:missionId" element={<Evaluation />} />
        <Route path="/reports" element={<Reports />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
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

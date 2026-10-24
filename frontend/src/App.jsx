import React, { useState } from "react";
import {
  BrowserRouter,
  NavLink,
  Routes,
  Route,
  useLocation,
  Link,
} from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  Boxes,
  BarChart3,
  BrainCircuit,
  ShieldCheck,
  Bell,
  ScrollText,
  Settings,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  LogOut,
  Hexagon,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import AlertsPage from "./pages/AlertsPage";
import LogsPage from "./pages/LogsPage";
import PredictionsPage from "./pages/PredictionsPage";
import ClusterPage from "./pages/ClusterPage";
import ObservabilityPage from "./pages/ObservabilityPage";
import HealingPage from "./pages/HealingPage";
import SettingsPage from "./pages/SettingsPage";
import { PlatformProvider, usePlatform } from "./hooks/useMetrics";
import { post } from "./services/api";

const pages = [
  ["/", "Overview", LayoutDashboard],
  ["/cluster", "Cluster explorer", Boxes],
  ["/observability", "Observability", BarChart3],
  ["/predictions", "AI fault intelligence", BrainCircuit],
  ["/healing", "Healing operations", ShieldCheck],
  ["/alerts", "Alerts & incidents", Bell],
  ["/logs", "Event & audit logs", ScrollText],
  ["/settings", "Settings & integrations", Settings],
];
function Login() {
  const { refresh, setAuthRequired } = usePlatform();
  const [username, setUsername] = useState("admin"),
    [password, setPassword] = useState(""),
    [error, setError] = useState("");
  return (
    <div className="login">
      <Hexagon size={32} />
      <h1>Connect to AutoHealOps</h1>
      <p>Use your configured administrator or viewer credentials.</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const r = await post("auth/login", { username, password });
            sessionStorage.setItem("token", r.access_token);
            setPassword("");
            setAuthRequired(false);
            refresh();
          } catch (err) {
            setError(err.message);
          }
        }}
      >
        <label>
          Username
          <input
            required
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            required
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p role="alert">{error}</p>}
        <button className="primary">Sign in</button>
      </form>
    </div>
  );
}
function Shell() {
  const {
    overview: o,
    loading,
    error,
    authRequired,
    refresh,
    status,
  } = usePlatform();
  const location = useLocation();
  const title =
    pages.find((x) => x[0] === location.pathname)?.[1] || "Not found";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <div className="brand-mark">
            <Hexagon size={29} />
            <Activity size={16} />
          </div>
          <div>
            AutoHeal<span>Ops</span>
            <small>INFRASTRUCTURE INTELLIGENCE</small>
          </div>
        </Link>
        <div className="workspace">
          <span className="workspace-icon">A</span>
          <div>
            Local workspace<small>{o?.cluster || "Connecting…"}</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <div className="nav-label">PLATFORM</div>
        <nav aria-label="Main navigation">
          {pages.slice(0, 5).map(([url, label, Icon]) => (
            <NavLink end to={url} key={url}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
          <div className="nav-label">OPERATIONS</div>
          {pages.slice(5).map(([url, label, Icon]) => (
            <NavLink end to={url} key={url}>
              <Icon size={18} />
              <span>{label}</span>
              {url === "/alerts" && o?.active_alerts > 0 && (
                <b className="nav-count">{o.active_alerts}</b>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="safety-note">
            <ShieldCheck size={18} />
            <strong>Safety comes standard</strong>
            <p>
              {o?.policy?.dry_run
                ? "Dry-run is active. Every action leaves an audit trail."
                : "Review active policy before executing a recovery."}
            </p>
            <Link to="/settings">
              View safeguards <ChevronRight size={12} />
            </Link>
          </div>
          <div className="user">
            <span className="avatar">MK</span>
            <div>
              Manikant Kumar<small>AutoHealOps workspace</small>
            </div>
            {sessionStorage.getItem("token") && (
              <button
                aria-label="Sign out"
                onClick={() => {
                  sessionStorage.removeItem("token");
                  window.location.reload();
                }}
              >
                <LogOut size={15} />
              </button>
            )}
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span className="muted">Workspace</span>
            <ChevronRight size={13} />
            <strong>{title}</strong>
          </div>
          <div>
            <span
              className={`connection ${status === "connected" ? "green" : "amber"}`}
            >
              <i />
              {status === "connected" ? "Live updates" : status}
            </span>
            <button
              className="icon-button"
              aria-label="Refresh application"
              onClick={refresh}
            >
              <RefreshCw size={16} />
            </button>
            <Link className="icon-button" aria-label="View alerts" to="/alerts">
              <Bell size={17} />
            </Link>
            <span className="avatar small">MK</span>
          </div>
        </header>
        {o?.simulated && (
          <div className="demo-banner">
            <span>
              <span className="demo-tag">DEMO</span>Simulated workloads and
              telemetry. Recovery actions never touch a real cluster.
            </span>
            <Link to="/settings">
              Environment details <ExternalLink size={12} />
            </Link>
          </div>
        )}
        <main id="main">
          <a href="#page-content" className="skip-link">
            Skip to page content
          </a>
          {authRequired ? (
            <Login />
          ) : (
            <>
              {error && (
                <div className="error-banner" role="alert">
                  {error} <button onClick={refresh}>Retry connection</button>
                </div>
              )}
              {loading ? (
                <div className="skeleton" aria-label="Loading operational data">
                  <div />
                  <div />
                  <div />
                </div>
              ) : (
                <div id="page-content">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/cluster" element={<ClusterPage />} />
                    <Route
                      path="/observability"
                      element={<ObservabilityPage />}
                    />
                    <Route path="/predictions" element={<PredictionsPage />} />
                    <Route path="/healing" element={<HealingPage />} />
                    <Route path="/alerts" element={<AlertsPage />} />
                    <Route path="/logs" element={<LogsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route
                      path="*"
                      element={
                        <>
                          <h1>Page not found</h1>
                          <Link to="/">Return to overview</Link>
                        </>
                      }
                    />
                  </Routes>
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              AutoHealOps <b>2.0</b> <span className="footer-divider">/</span>{" "}
              Built for resilient infrastructure
            </span>
            <span>
              {o?.simulated
                ? "DEMONSTRATION ENVIRONMENT"
                : "OPERATIONS CONSOLE"}{" "}
              <i />
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <PlatformProvider>
        <Shell />
      </PlatformProvider>
    </BrowserRouter>
  );
}

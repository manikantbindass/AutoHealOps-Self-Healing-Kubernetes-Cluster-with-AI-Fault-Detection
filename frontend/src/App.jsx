import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import AlertsPage from './pages/AlertsPage';
import LogsPage from './pages/LogsPage';
import PredictionsPage from './pages/PredictionsPage';

function NavLink({ to, children }) {
  const location = useLocation();
  const active = location.pathname === to;
  return (
    <Link to={to} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
      active ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-gray-400 hover:text-white hover:bg-white/10'
    }`}>{children}</Link>
  );
}

function Nav() {
  return (
    <nav className="glass border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full animated-border p-0.5">
          <div className="w-full h-full rounded-full bg-[#0f0c29] flex items-center justify-center text-sm">🧠</div>
        </div>
        <span className="text-cyan-400 font-bold text-lg tracking-wide">AutoHealOps</span>
        <span className="text-xs text-gray-500 px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full border border-green-500/30">● Live</span>
      </div>
      <div className="flex gap-2">
        <NavLink to="/">Dashboard</NavLink>
        <NavLink to="/alerts">Alerts</NavLink>
        <NavLink to="/predictions">AI Predictions</NavLink>
        <NavLink to="/logs">Logs</NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <Router>
      <div className="min-h-screen">
        <Nav />
        <main className="p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/logs" element={<LogsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

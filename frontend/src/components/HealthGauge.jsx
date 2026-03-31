import React from 'react';

export default function HealthGauge({ score }) {
  const color = score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';
  const label = score >= 80 ? 'Healthy' : score >= 50 ? 'Warning' : 'Critical';
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="glass border border-white/10 p-6 rounded-xl flex flex-col items-center">
      <p className="text-gray-400 text-xs font-medium uppercase tracking-widest mb-4">Cluster Health</p>
      <div className="relative w-36 h-36">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="10" />
          <circle cx="60" cy="60" r="54" fill="none" stroke={color}
            strokeWidth="10" strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-mono" style={{ color }}>{score}</span>
          <span className="text-xs" style={{ color }}>{label}</span>
        </div>
      </div>
    </div>
  );
}

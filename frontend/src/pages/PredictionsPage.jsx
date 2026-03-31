import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const MOCK = [
  { metric: 'CPU', probability: 0.78, ttf: 12 },
  { metric: 'Memory', probability: 0.45, ttf: 35 },
  { metric: 'Network', probability: 0.22, ttf: 90 },
  { metric: 'Pod Health', probability: 0.61, ttf: 20 },
];

export default function PredictionsPage() {
  const [predictions] = useState(MOCK);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">🧠 AI Failure Predictions</h1>
      <p className="text-gray-400 text-sm">LSTM model predicts failure probability and estimated time-to-failure.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {predictions.map(p => (
          <div key={p.metric} className="glass border border-white/10 p-5 rounded-xl">
            <p className="text-gray-400 text-xs uppercase tracking-widest">{p.metric}</p>
            <p className="text-3xl font-bold font-mono mt-2" style={{ color: p.probability > 0.7 ? '#ef4444' : p.probability > 0.4 ? '#f59e0b' : '#10b981' }}>
              {(p.probability * 100).toFixed(0)}%
            </p>
            <p className="text-gray-400 text-xs mt-1">Failure probability</p>
            <p className="text-cyan-400 text-sm mt-2 font-mono">⏱ ~{p.ttf} min</p>
            <p className="text-gray-500 text-xs">Time to failure</p>
          </div>
        ))}
      </div>
      <div className="glass border border-white/10 p-5 rounded-xl">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Failure Probability by Component</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={predictions}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="metric" tick={{ fill: '#6b7280', fontSize: 12 }} />
            <YAxis domain={[0, 1]} tick={{ fill: '#6b7280', fontSize: 12 }} />
            <Tooltip formatter={v => `${(v*100).toFixed(0)}%`} contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
            <Bar dataKey="probability" fill="#00fff0" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

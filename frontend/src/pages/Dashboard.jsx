import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import MetricCard from '../components/MetricCard';
import HealthGauge from '../components/HealthGauge';
import { useMetrics } from '../hooks/useMetrics';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Dashboard() {
  const { metrics, healthScore, history, loading } = useMetrics(5000);
  const { isConnected } = useWebSocket();

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-cyan-400 animate-pulse text-xl">🧠 Loading metrics...</div>
    </div>
  );

  const cards = [
    { title: 'CPU Usage', value: metrics ? (metrics.cpu_usage * 100).toFixed(1) : 0, unit: '%', icon: '💻', color: metrics?.cpu_usage > 0.8 ? 'red' : 'cyan' },
    { title: 'Memory Usage', value: metrics ? (metrics.memory_usage * 100).toFixed(1) : 0, unit: '%', icon: '🧠', color: metrics?.memory_usage > 0.8 ? 'red' : 'purple' },
    { title: 'Pod Restarts', value: metrics?.pod_restarts ?? 0, unit: '', icon: '🔄', color: metrics?.pod_restarts > 5 ? 'red' : 'yellow' },
    { title: 'Network Latency', value: metrics ? metrics.network_latency.toFixed(0) : 0, unit: 'ms', icon: '🌐', color: metrics?.network_latency > 400 ? 'red' : 'green' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Cluster Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">Real-time Kubernetes metrics & AI anomaly detection</p>
        </div>
        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${
          isConnected ? 'border-green-500/40 bg-green-500/10 text-green-400' : 'border-red-500/40 bg-red-500/10 text-red-400'
        }`}>
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          {isConnected ? 'Live' : 'Reconnecting...'}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="md:col-span-1">
          <HealthGauge score={healthScore ?? 0} />
        </div>
        <div className="md:col-span-4 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map(c => <MetricCard key={c.title} {...c} />)}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass border border-white/10 p-5 rounded-xl">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">CPU & Memory Trends</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={history}>
              <defs>
                <linearGradient id="cpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00fff0" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00fff0" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="mem" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
              <Area type="monotone" dataKey="cpu_usage" stroke="#00fff0" fill="url(#cpu)" name="CPU" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="memory_usage" stroke="#a855f7" fill="url(#mem)" name="Memory" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="glass border border-white/10 p-5 rounded-xl">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Network Latency (ms)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
              <Line type="monotone" dataKey="network_latency" stroke="#10b981" strokeWidth={2} dot={false} name="Latency" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

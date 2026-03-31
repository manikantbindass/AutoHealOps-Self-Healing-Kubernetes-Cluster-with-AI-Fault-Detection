import React from 'react';

const MOCK_LOGS = [
  { timestamp: new Date().toISOString(), action: 'restart_pod', target: 'backend-pod-xyz', result: 'success', triggered_by: 'auto' },
  { timestamp: new Date(Date.now()-120000).toISOString(), action: 'scale_deployment', target: 'backend', result: 'scaled to 3 replicas', triggered_by: 'auto' },
  { timestamp: new Date(Date.now()-300000).toISOString(), action: 'reschedule_pods', target: 'node-2', result: 'rescheduled 2 pods', triggered_by: 'manual' },
  { timestamp: new Date(Date.now()-600000).toISOString(), action: 'restart_pod', target: 'ai-engine-pod', result: 'success', triggered_by: 'auto' },
];

const actionColors = {
  restart_pod: 'text-blue-400',
  scale_deployment: 'text-green-400',
  reschedule_pods: 'text-yellow-400',
};

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">📄 Healing Action Logs</h1>
      <div className="glass border border-white/10 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5">
            <tr>
              {['Timestamp', 'Action', 'Target', 'Result', 'Triggered By'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {MOCK_LOGS.map((log, i) => (
              <tr key={i} className="hover:bg-white/5 transition-colors">
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">{new Date(log.timestamp).toLocaleString()}</td>
                <td className={`px-4 py-3 font-medium ${actionColors[log.action] || 'text-white'}`}>{log.action}</td>
                <td className="px-4 py-3 text-gray-300 font-mono text-xs">{log.target}</td>
                <td className="px-4 py-3 text-gray-300">{log.result}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    log.triggered_by === 'auto' ? 'border-cyan-500/40 text-cyan-400' : 'border-purple-500/40 text-purple-400'
                  }`}>{log.triggered_by}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

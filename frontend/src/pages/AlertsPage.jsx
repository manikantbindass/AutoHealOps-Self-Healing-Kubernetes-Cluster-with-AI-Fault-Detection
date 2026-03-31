import React, { useState, useEffect } from 'react';
import AlertBadge from '../components/AlertBadge';
import { apiService } from '../services/api';

const MOCK_ALERTS = [
  { _id: '1', severity: 'CRITICAL', message: 'CPU usage spiked to 94%', timestamp: new Date().toISOString(), status: 'open' },
  { _id: '2', severity: 'HIGH', message: 'Pod autohealops-backend-xyz restarted 8 times', timestamp: new Date(Date.now()-60000).toISOString(), status: 'open' },
  { _id: '3', severity: 'MEDIUM', message: 'Network latency > 450ms for 5 minutes', timestamp: new Date(Date.now()-300000).toISOString(), status: 'acknowledged' },
  { _id: '4', severity: 'LOW', message: 'Memory usage at 72%', timestamp: new Date(Date.now()-600000).toISOString(), status: 'resolved' },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState(MOCK_ALERTS);

  useEffect(() => {
    apiService.getAlerts().then(r => { if (r.data?.length) setAlerts(r.data); }).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">🚨 Active Alerts</h1>
      <div className="space-y-3">
        {alerts.map(alert => (
          <div key={alert._id} className="glass border border-white/10 p-4 rounded-xl flex items-start justify-between gap-4 fade-in-up">
            <div className="flex items-start gap-3">
              <AlertBadge severity={alert.severity} />
              <div>
                <p className="text-white text-sm font-medium">{alert.message}</p>
                <p className="text-gray-500 text-xs mt-1">{new Date(alert.timestamp).toLocaleString()}</p>
              </div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full border ${
              alert.status === 'open' ? 'border-red-500/40 text-red-400' :
              alert.status === 'acknowledged' ? 'border-yellow-500/40 text-yellow-400' :
              'border-green-500/40 text-green-400'
            }`}>{alert.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

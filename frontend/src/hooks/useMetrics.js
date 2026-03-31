import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';

export function useMetrics(refreshInterval = 5000) {
  const [metrics, setMetrics] = useState(null);
  const [healthScore, setHealthScore] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([
        apiService.getMetrics(),
        apiService.getHealthScore(),
      ]);
      setMetrics(m.data);
      setHealthScore(h.health_score);
      setHistory(prev => [
        ...prev.slice(-29),
        { ...m.data, time: new Date().toLocaleTimeString() }
      ]);
      setLoading(false);
    } catch (e) {
      // Use mock data if API not reachable
      const mock = {
        cpu_usage: parseFloat((Math.random() * 0.8 + 0.1).toFixed(3)),
        memory_usage: parseFloat((Math.random() * 0.7 + 0.2).toFixed(3)),
        pod_restarts: Math.floor(Math.random() * 10),
        network_latency: parseFloat((Math.random() * 400 + 50).toFixed(1)),
      };
      setMetrics(mock);
      setHealthScore(Math.floor(Math.random() * 40 + 55));
      setHistory(prev => [...prev.slice(-29), { ...mock, time: new Date().toLocaleTimeString() }]);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  return { metrics, healthScore, history, loading };
}

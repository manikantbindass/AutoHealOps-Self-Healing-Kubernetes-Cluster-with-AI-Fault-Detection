import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { get, post, put } from "../services/api";
import { useWebSocket } from "./useWebSocket";

const Context = createContext(null);
const resources = {
  history: "metrics?limit=200",
  alerts: "alerts?limit=200",
  anomalies: "anomalies?limit=200",
  actions: "healing/actions?limit=200",
  audit: "audit/events?limit=200",
  clusters: "clusters",
  predictions: "predictions",
  integrations: "integrations/status",
};
export function PlatformProvider({ children }) {
  const [overview, setOverview] = useState(null);
  const [data, setData] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [busy, setBusy] = useState(false);
  const inflight = useRef(false);
  const mounted = useRef(true);
  const refresh = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    try {
      const result = await get("overview");
      if (!mounted.current) return;
      setOverview(result);
      setAuthRequired(false);
      const entries = await Promise.all(
        Object.entries(resources).map(async ([key, path]) => [
          key,
          await get(path),
        ]),
      );
      if (mounted.current) {
        setData(Object.fromEntries(entries));
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e.message);
    } finally {
      inflight.current = false;
      if (mounted.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    mounted.current = true;
    const requireAuth = () => setAuthRequired(true);
    window.addEventListener("auth-required", requireAuth);
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => {
      mounted.current = false;
      clearInterval(timer);
      window.removeEventListener("auth-required", requireAuth);
    };
  }, [refresh]);
  const update = useCallback((value) => setOverview(value), []);
  const { status } = useWebSocket(update, !!overview && !authRequired);
  const mutate = async (path, body, method = "post") => {
    setBusy(true);
    setError("");
    try {
      const result = await (method === "put"
        ? put(path, body)
        : post(path, body));
      await refresh();
      return result;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy(false);
    }
  };
  return (
    <Context.Provider
      value={{
        overview,
        data,
        error,
        loading,
        authRequired,
        setAuthRequired,
        refresh,
        status,
        mutate,
        busy,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const usePlatform = () => useContext(Context);
// Dashboard and all pages share one collector and one WebSocket connection.
export function useMetrics() {
  return usePlatform();
}

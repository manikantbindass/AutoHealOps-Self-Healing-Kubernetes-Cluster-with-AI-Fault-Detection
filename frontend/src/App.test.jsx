import { vi } from "vitest";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { usePlatform } from "./hooks/useMetrics";
import AlertsPage from "./pages/AlertsPage";
import HealingPage from "./pages/HealingPage";
import ClusterPage from "./pages/ClusterPage";
import PredictionsPage from "./pages/PredictionsPage";
import { useWebSocket } from "./hooks/useWebSocket";
vi.mock("./hooks/useMetrics", () => ({ usePlatform: vi.fn() }));
let host, root;
const mutate = vi.fn();
const base = {
  overview: {
    policy: {
      paused: false,
      dry_run: true,
      healing_mode: "manual",
      namespace: "autohealops",
      max_replicas: 5,
      cooldown_seconds: 300,
    },
    simulated: true,
  },
  data: {
    alerts: { items: [] },
    actions: { items: [] },
    clusters: { items: [{ workloads: [] }] },
    anomalies: { items: [] },
  },
  mutate,
  busy: false,
  refresh: vi.fn(),
};
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  usePlatform.mockReturnValue(base);
  mutate.mockClear();
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.useRealTimers();
});
function mountPage(node) {
  act(() => root.render(<MemoryRouter>{node}</MemoryRouter>));
}
test("empty alerts show a useful state", () => {
  mountPage(<AlertsPage />);
  expect(host.textContent).toContain("No incidents match");
});
test("incident acknowledgement calls real API path", () => {
  usePlatform.mockReturnValue({
    ...base,
    data: {
      alerts: {
        items: [
          {
            id: "one",
            target: "checkout",
            severity: "critical",
            status: "open",
            timestamp: "2026-10-24T10:00:00Z",
            message: "CPU elevated",
          },
        ],
      },
    },
  });
  mountPage(<AlertsPage />);
  act(() =>
    [...host.querySelectorAll("button")]
      .find((x) => x.textContent === "Acknowledge")
      .click(),
  );
  expect(mutate).toHaveBeenCalledWith("alerts/one/acknowledge");
});
test("approval workflow uses reviewed rationale", () => {
  usePlatform.mockReturnValue({
    ...base,
    data: {
      actions: {
        items: [
          {
            id: "a",
            status: "recommended",
            action: "restart_deployment",
            target: "checkout",
            namespace: "autohealops",
            timestamp: "2026-10-24T10:00:00Z",
            attempts: 0,
            result: "Awaiting review",
          },
        ],
      },
    },
  });
  mountPage(<HealingPage />);
  act(() =>
    [...host.querySelectorAll("button")]
      .find((x) => x.textContent === "Approve action")
      .click(),
  );
  expect(mutate).toHaveBeenCalledWith("healing/actions/a/approve", {
    rationale: "Reviewed evidence and approved controlled recovery",
  });
});
test("cluster details expose available resource values", () => {
  usePlatform.mockReturnValue({
    ...base,
    data: {
      clusters: {
        items: [
          {
            workloads: [
              {
                id: "pod",
                name: "checkout-1",
                namespace: "autohealops",
                kind: "Pod",
                status: "Running",
                restarts: 3,
              },
            ],
          },
        ],
      },
    },
  });
  mountPage(<ClusterPage />);
  act(() =>
    [...host.querySelectorAll("button")]
      .find((x) => x.textContent === "Inspect")
      .click(),
  );
  expect(host.querySelector('[role="dialog"]').textContent).toContain(
    "restarts",
  );
});
test("intelligence page never invents probability", () => {
  mountPage(<PredictionsPage />);
  expect(host.textContent).toContain("No calibrated failure probability");
});
test("websocket reconnect uses exponential delays and stops on unmount", () => {
  vi.useFakeTimers();
  const instances = [];
  global.WebSocket = vi.fn(function () {
    const ws = { close: vi.fn(), send: vi.fn() };
    instances.push(ws);
    return ws;
  });
  const update = vi.fn();
  function Probe() {
    const { status } = useWebSocket(update);
    return <span>{status}</span>;
  }
  mountPage(<Probe />);
  expect(instances).toHaveLength(1);
  act(() => instances[0].onclose());
  act(() => vi.advanceTimersByTime(1000));
  expect(instances).toHaveLength(2);
  act(() => instances[1].onclose());
  act(() => vi.advanceTimersByTime(1999));
  expect(instances).toHaveLength(2);
  act(() => vi.advanceTimersByTime(1));
  expect(instances).toHaveLength(3);
  act(() => root.unmount());
  root = createRoot(host);
  act(() => vi.runOnlyPendingTimers());
  expect(instances).toHaveLength(3);
});

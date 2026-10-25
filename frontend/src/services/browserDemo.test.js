import { afterEach, beforeEach, expect, test, vi } from "vitest";
afterEach(() => vi.useRealTimers());
let demoRequest;
beforeEach(async () => {
  sessionStorage.clear();
  vi.resetModules();
  ({ demoRequest } = await import("./browserDemo"));
});
test("public simulation identifies rules, no database and no failure probability", async () => {
  const overview = await demoRequest("get", "overview");
  expect(overview.hosting).toBe("browser-showcase");
  expect(overview.simulated).toBe(true);
  expect((await demoRequest("get", "integrations/status")).storage).toContain(
    "browser session",
  );
  expect((await demoRequest("get", "predictions")).available).toBe(false);
});
test("fault, approval, pause, recovery and idempotency are isolated and auditable", async () => {
  await demoRequest("post", "demo/scenarios", { scenario: "cpu" });
  const [{ id }] = (await demoRequest("get", "healing/actions")).items;
  expect((await demoRequest("get", "anomalies")).items[0].source).toBe(
    "rule-based",
  );
  await expect(
    demoRequest("post", `healing/actions/${id}/execute`),
  ).rejects.toThrow("Resume healing");
  await demoRequest("put", "settings", {
    paused: false,
    healing_mode: "manual",
  });
  await expect(
    demoRequest("post", `healing/actions/${id}/execute`),
  ).rejects.toThrow("approval");
  await demoRequest("post", `healing/actions/${id}/approve`, {
    rationale: "Reviewed synthetic evidence",
  });
  const completed = await demoRequest("post", `healing/actions/${id}/execute`);
  expect(completed.status).toBe("simulated");
  expect(completed.before.cpu_usage).toBe(0.96);
  expect(completed.after.cpu_usage).toBeLessThan(0.8);
  expect(
    (await demoRequest("post", `healing/actions/${id}/execute`)).attempts,
  ).toBe(1);
  expect(
    (await demoRequest("get", "audit/events")).items.some(
      (x) => x.action === "execute_completed",
    ),
  ).toBe(true);
});
test("namespace, replica, automatic policy and arbitrary action boundaries are enforced", async () => {
  const body = {
    action: "scale_deployment",
    namespace: "autohealops",
    target: "api-gateway",
    replicas: 6,
    rationale: "Synthetic capacity test",
  };
  await expect(demoRequest("post", "healing/actions", body)).rejects.toThrow(
    "Replicas",
  );
  await expect(
    demoRequest("post", "healing/actions", {
      ...body,
      namespace: "kube-system",
    }),
  ).rejects.toThrow("managed");
  await expect(
    demoRequest("put", "settings", {
      paused: false,
      healing_mode: "unknown",
    }),
  ).rejects.toThrow("Choose");
  await expect(
    demoRequest("post", "demo/scenarios", { scenario: "delete" }),
  ).rejects.toThrow("Unknown");
});
test("reset resolves incidents and preserves history; duplicate scenarios dedupe", async () => {
  await demoRequest("post", "demo/scenarios", { scenario: "memory" });
  await demoRequest("post", "demo/scenarios", { scenario: "memory" });
  expect((await demoRequest("get", "alerts")).total).toBe(1);
  await demoRequest("post", "demo/scenarios", { scenario: "reset" });
  expect((await demoRequest("get", "alerts")).items[0].status).toBe("resolved");
  expect((await demoRequest("get", "anomalies")).total).toBe(1);
});

test("automatic simulation confirms three samples then recovers without approval", async () => {
  vi.useFakeTimers();
  await demoRequest("put", "settings", {
    paused: false,
    healing_mode: "automatic",
  });
  await demoRequest("post", "demo/scenarios", { scenario: "cpu" });
  expect((await demoRequest("get", "healing/actions")).items[0].status).toBe(
    "recommended",
  );
  vi.setSystemTime(Date.now() + 5000);
  await demoRequest("get", "overview");
  expect((await demoRequest("get", "healing/actions")).items[0].status).toBe(
    "recommended",
  );
  vi.setSystemTime(Date.now() + 5000);
  const overview = await demoRequest("get", "overview");
  const item = (await demoRequest("get", "healing/actions")).items[0];
  expect(item.status).toBe("simulated");
  expect(item.approved_by).toBeNull();
  expect(item.attempts).toBe(1);
  expect(overview.metrics.cpu_usage).toBeLessThan(0.8);
  expect((await demoRequest("get", "alerts")).items[0].status).toBe("resolved");
  vi.resetModules();
  ({ demoRequest } = await import("./browserDemo"));
  expect((await demoRequest("get", "settings")).paused).toBe(true);
});

test("automatic simulation keeps operator-created actions behind approval", async () => {
  await demoRequest("put", "settings", {
    paused: false,
    healing_mode: "automatic",
  });
  const item = await demoRequest("post", "healing/actions", {
    action: "restart_deployment",
    namespace: "autohealops",
    target: "api-gateway",
    replicas: null,
    rationale: "Operator selected this workload",
  });
  await expect(
    demoRequest("post", `healing/actions/${item.id}/execute`),
  ).rejects.toThrow("approval");
});

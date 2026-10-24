"""Deployment-only, opt-in, namespace-scoped Kubernetes operations."""

import time
from datetime import UTC, datetime


class KubernetesAdapter:
    def __init__(self, namespace):
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        self.apps = client.AppsV1Api()
        self.core = client.CoreV1Api()
        self.namespace = namespace

    def workloads(self):
        pods = self.core.list_namespaced_pod(self.namespace, _request_timeout=5).items
        deploys = self.apps.list_namespaced_deployment(self.namespace, _request_timeout=5).items
        rows = []
        for d in deploys:
            rows.append(
                dict(
                    id=d.metadata.uid,
                    name=d.metadata.name,
                    namespace=self.namespace,
                    kind="Deployment",
                    status="Healthy"
                    if (d.status.ready_replicas or 0) == (d.spec.replicas or 0)
                    else "Degraded",
                    replicas=d.spec.replicas or 0,
                    ready=d.status.ready_replicas or 0,
                    managed=(d.metadata.labels or {}).get("autohealops.io/managed") == "true",
                )
            )
        for p in pods:
            rows.append(
                dict(
                    id=p.metadata.uid,
                    name=p.metadata.name,
                    namespace=self.namespace,
                    kind="Pod",
                    status=p.status.phase,
                    restarts=sum(x.restart_count for x in (p.status.container_statuses or [])),
                    node=p.spec.node_name,
                    managed=False,
                )
            )
        rows.append(
            dict(
                id=self.namespace,
                name=self.namespace,
                namespace=self.namespace,
                kind="Namespace",
                status="Connected",
                managed=False,
            )
        )
        return rows

    def execute(self, action, max_replicas):
        if action["namespace"] != self.namespace:
            raise ValueError("Namespace outside authorized boundary")
        d = self.apps.read_namespaced_deployment(
            action["target"], self.namespace, _request_timeout=5
        )
        if (d.metadata.labels or {}).get("autohealops.io/managed") != "true":
            raise ValueError("Deployment must be labelled autohealops.io/managed=true")
        if action["action"] == "scale_deployment":
            replicas = action.get("replicas")
            if replicas is None or not 1 <= replicas <= max_replicas:
                raise ValueError("Replica limit exceeded")
            self.apps.patch_namespaced_deployment_scale(
                action["target"],
                self.namespace,
                {"spec": {"replicas": replicas}},
                _request_timeout=5,
            )
        else:
            replicas = d.spec.replicas or 1
            self.apps.patch_namespaced_deployment(
                action["target"],
                self.namespace,
                {
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": datetime.now(
                                        UTC
                                    ).isoformat()
                                }
                            }
                        }
                    }
                },
                _request_timeout=5,
            )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            latest = self.apps.read_namespaced_deployment(
                action["target"], self.namespace, _request_timeout=5
            )
            s = latest.status
            if (
                (s.observed_generation or 0) >= latest.metadata.generation
                and (s.updated_replicas or 0) == replicas
                and (s.available_replicas or 0) == replicas
            ):
                return {
                    "verified": True,
                    "ready_replicas": replicas,
                    "verification": "Rollout available; subsequent telemetry determines metric recovery",
                }
            time.sleep(2)
        raise TimeoutError("Mutation accepted; rollout recovery not verified within 45 seconds")

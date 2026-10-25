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
        self.autoscaling = client.AutoscalingV1Api()
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
        if action.get("autonomous"):
            if (d.metadata.labels or {}).get("autohealops.io/autonomous") != "true":
                raise ValueError("Deployment no longer permits autonomous recovery")
            if d.metadata.uid != action.get("target_uid"):
                raise ValueError("Deployment identity changed since detection")
            if d.metadata.generation != action.get("target_generation"):
                raise ValueError("Deployment changed since detection")
            if d.spec.paused or (d.spec.replicas or 0) < 1:
                raise ValueError("Paused or stopped Deployment cannot be healed automatically")
            if self.autoscaling.list_namespaced_horizontal_pod_autoscaler(
                self.namespace, _request_timeout=5
            ).items:
                raise ValueError("Autonomous actions require a namespace without HPAs")
        if action["action"] == "scale_deployment":
            replicas = action.get("replicas")
            if replicas is None or not 1 <= replicas <= max_replicas:
                raise ValueError("Replica limit exceeded")
            self.apps.patch_namespaced_deployment_scale(
                action["target"],
                self.namespace,
                {
                    "spec": {"replicas": replicas},
                    **(
                        {"metadata": {"resourceVersion": d.metadata.resource_version}}
                        if action.get("autonomous")
                        else {}
                    ),
                },
                _request_timeout=5,
            )
        elif action["action"] == "restart_deployment":
            replicas = d.spec.replicas or 1
            self.apps.patch_namespaced_deployment(
                action["target"],
                self.namespace,
                {
                    **(
                        {"metadata": {"resourceVersion": d.metadata.resource_version}}
                        if action.get("autonomous")
                        else {}
                    ),
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
                    },
                },
                _request_timeout=5,
            )
        else:
            raise ValueError("Unsupported Deployment operation")
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

    def autonomous_snapshot(self, target):
        """Resolve exact Deployment -> ReplicaSet -> Pod ownership, never name prefixes."""
        d = self.apps.read_namespaced_deployment(target, self.namespace, _request_timeout=5)
        labels = d.metadata.labels or {}
        if any(
            labels.get(k) != "true" for k in ("autohealops.io/managed", "autohealops.io/autonomous")
        ):
            raise ValueError("Both managed and autonomous labels must be true")
        if d.spec.paused or not d.spec.replicas:
            raise ValueError("Paused or stopped Deployment")
        # HPA is served by autoscaling/v1, not AppsV1Api.
        if self.autoscaling.list_namespaced_horizontal_pod_autoscaler(
            self.namespace, _request_timeout=5
        ).items:
            raise ValueError("Autonomous actions require a namespace without HPAs")
        sets = self.apps.list_namespaced_replica_set(self.namespace, _request_timeout=5).items
        owned = {
            r.metadata.uid
            for r in sets
            if any(
                o.uid == d.metadata.uid and o.kind == "Deployment" and o.controller
                for o in (r.metadata.owner_references or [])
            )
        }
        pods = self.core.list_namespaced_pod(self.namespace, _request_timeout=5).items
        names = sorted(
            p.metadata.name
            for p in pods
            if not p.metadata.deletion_timestamp
            and any(
                o.uid in owned and o.kind == "ReplicaSet" and o.controller
                for o in (p.metadata.owner_references or [])
            )
        )
        if not names:
            raise ValueError("No owned active Pods available")
        return dict(
            uid=d.metadata.uid,
            generation=d.metadata.generation,
            replicas=d.spec.replicas,
            pods=names,
        )

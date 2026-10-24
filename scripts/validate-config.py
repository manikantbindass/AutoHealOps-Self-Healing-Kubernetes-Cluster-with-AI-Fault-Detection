"""Static consistency checks, not Kubernetes server admission validation."""

import json
import re
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
objects = []
for p in (root / "k8s").rglob("*.yaml"):
    objects.extend(x for x in yaml.safe_load_all(p.read_text(encoding="utf-8")) if x)
assert objects
for obj in objects:
    assert obj["apiVersion"] and obj["kind"] and obj["metadata"]["name"]
    assert obj["kind"] not in ("ClusterRole", "ClusterRoleBinding")
    if obj["kind"] != "Namespace":
        assert obj["metadata"]["namespace"] == "autohealops"
    if obj["kind"] == "Role":
        assert all("delete" not in r["verbs"] and "*" not in r["resources"] for r in obj["rules"])
    if obj["kind"] == "Deployment":
        for c in obj["spec"]["template"]["spec"]["containers"]:
            assert all(
                k in c for k in ("resources", "startupProbe", "readinessProbe", "livenessProbe")
            )
            assert ":latest" not in c["image"]
        if obj["metadata"]["name"] == "autohealops-backend":
            assert obj["spec"]["replicas"] == 1
prom = yaml.safe_load((root / "monitoring/prometheus.yml").read_text(encoding="utf-8"))
assert any(job.get("metrics_path") == "/telemetry" for job in prom["scrape_configs"])
dashboard = json.loads((root / "monitoring/grafana/dashboard.json").read_text(encoding="utf-8"))
assert len(dashboard["panels"]) >= 6
for match in re.findall(
    r"!\[[^\]]*\]\((docs/screenshots/[^)]+)\)", (root / "README.md").read_text(encoding="utf-8")
):
    assert (root / match).is_file(), f"Missing screenshot {match}"
print(
    f"Static checks passed: {len(objects)} Kubernetes objects, monitoring queries/provisioning, README image paths. No cluster admission or runtime claim."
)

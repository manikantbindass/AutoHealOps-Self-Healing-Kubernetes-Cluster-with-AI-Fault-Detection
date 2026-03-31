"""AutoHealOps - Automated Self-Healing Script
Runs continuously, polls AI engine, and takes healing actions.
"""
import time
import httpx
import os
from datetime import datetime
from kubernetes import client, config

AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
POLL_INTERVAL = int(os.getenv("HEAL_POLL_INTERVAL", "30"))

def load_k8s():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

def get_current_metrics():
    try:
        r = httpx.get(f"{BACKEND_URL}/metrics", timeout=5)
        return r.json().get("data", {})
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ Could not fetch metrics: {e}")
        return {}

def check_anomaly(metrics):
    try:
        r = httpx.post(f"{AI_ENGINE_URL}/detect", json=metrics, timeout=5)
        return r.json()
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ AI Engine unreachable: {e}")
        return None

def heal(anomaly_result, metrics):
    if not anomaly_result or not anomaly_result.get("is_anomaly"):
        return

    severity = anomaly_result.get("severity", "LOW")
    print(f"[{datetime.now()}] 🚨 Anomaly detected! Severity: {severity}")

    try:
        load_k8s()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        if severity in ["HIGH", "CRITICAL"]:
            # Restart non-running pods
            pods = v1.list_namespaced_pod("default")
            for pod in pods.items:
                if pod.status.phase != "Running":
                    v1.delete_namespaced_pod(pod.metadata.name, "default")
                    print(f"  ✅ Restarted pod: {pod.metadata.name}")

        if metrics.get("cpu_usage", 0) > 0.85:
            # Scale up deployments
            deploys = apps_v1.list_namespaced_deployment("default")
            for d in deploys.items:
                current = d.spec.replicas or 1
                new_replicas = min(current + 1, 5)
                body = {"spec": {"replicas": new_replicas}}
                apps_v1.patch_namespaced_deployment_scale(d.metadata.name, "default", body)
                print(f"  ✅ Scaled {d.metadata.name} to {new_replicas} replicas")

    except Exception as e:
        print(f"  ❌ Healing failed: {e}")

def main():
    print(f"🔧 AutoHealOps self-healing loop started (interval: {POLL_INTERVAL}s)")
    while True:
        metrics = get_current_metrics()
        if metrics:
            result = check_anomaly(metrics)
            heal(result, metrics)
        else:
            print(f"[{datetime.now()}] ⏳ Waiting for metrics...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

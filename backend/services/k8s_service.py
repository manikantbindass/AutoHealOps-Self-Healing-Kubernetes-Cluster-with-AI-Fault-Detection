"""Kubernetes API service for self-healing actions"""
from kubernetes import client, config
import os

def load_k8s_config():
    try:
        config.load_incluster_config()  # Inside k8s pod
    except:
        config.load_kube_config()       # Local kubeconfig

def restart_pod(namespace: str, pod_name: str):
    """Delete pod (Kubernetes will recreate it automatically)"""
    load_k8s_config()
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod {pod_name} deleted (will restart automatically)"
    except Exception as e:
        return f"Error restarting pod: {str(e)}"

def scale_deployment(namespace: str, deployment_name: str, replicas: int):
    """Scale a deployment to the given replica count"""
    load_k8s_config()
    apps_v1 = client.AppsV1Api()
    try:
        body = {"spec": {"replicas": replicas}}
        apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name, namespace=namespace, body=body
        )
        return f"Scaled {deployment_name} to {replicas} replicas"
    except Exception as e:
        return f"Error scaling: {str(e)}"

def reschedule_pods(namespace: str):
    """Force pod rescheduling by adding annotation"""
    load_k8s_config()
    v1 = client.CoreV1Api()
    try:
        pods = v1.list_namespaced_pod(namespace=namespace)
        rescheduled = []
        for pod in pods.items:
            if pod.status.phase != "Running":
                v1.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)
                rescheduled.append(pod.metadata.name)
        return f"Rescheduled pods: {rescheduled}"
    except Exception as e:
        return f"Error rescheduling: {str(e)}"

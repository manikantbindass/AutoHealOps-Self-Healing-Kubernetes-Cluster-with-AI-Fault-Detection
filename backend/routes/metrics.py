"""Metrics API routes"""
from fastapi import APIRouter, Query
from services.prometheus_service import fetch_metrics
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_current_metrics():
    """Get current cluster metrics from Prometheus"""
    metrics = await fetch_metrics()
    return {"status": "ok", "data": metrics, "timestamp": datetime.utcnow().isoformat()}

@router.get("/history")
async def get_metric_history(metric: str = Query(default="cpu"), limit: int = 100):
    """Get historical metrics from MongoDB"""
    from services.db import get_db
    db = get_db()
    records = await db["metrics"].find({"metric": metric}).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"status": "ok", "data": records}

@router.get("/health-score")
async def get_health_score():
    """Calculate overall cluster health score (0-100)"""
    metrics = await fetch_metrics()
    cpu = metrics.get("cpu_usage", 0.5)
    memory = metrics.get("memory_usage", 0.5)
    restarts = min(metrics.get("pod_restarts", 0) / 10, 1.0)
    latency = min(metrics.get("network_latency", 100) / 1000, 1.0)
    score = int((1 - (cpu * 0.3 + memory * 0.3 + restarts * 0.2 + latency * 0.2)) * 100)
    return {"health_score": max(0, min(100, score)), "timestamp": datetime.utcnow().isoformat()}

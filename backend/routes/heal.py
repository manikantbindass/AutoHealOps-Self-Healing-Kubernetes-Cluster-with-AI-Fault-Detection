"""Self-Healing API routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.k8s_service import restart_pod, scale_deployment, reschedule_pods
from services.db import get_db
from datetime import datetime

router = APIRouter()

class HealRequest(BaseModel):
    action: str  # restart_pod | scale_deployment | reschedule_pods
    namespace: str = "default"
    target: str   # pod name or deployment name
    replicas: int = None

@router.post("/")
async def trigger_healing(req: HealRequest):
    """Manually trigger a healing action"""
    result = None
    if req.action == "restart_pod":
        result = restart_pod(req.namespace, req.target)
    elif req.action == "scale_deployment":
        result = scale_deployment(req.namespace, req.target, req.replicas or 3)
    elif req.action == "reschedule_pods":
        result = reschedule_pods(req.namespace)
    else:
        raise HTTPException(status_code=400, detail="Unknown action")
    
    # Log the action
    db = get_db()
    await db["healing_logs"].insert_one({
        "action": req.action, "target": req.target,
        "namespace": req.namespace, "result": str(result),
        "timestamp": datetime.utcnow().isoformat(), "triggered_by": "manual"
    })
    return {"status": "ok", "action": req.action, "result": str(result)}

@router.get("/logs")
async def get_healing_logs(limit: int = 50):
    """Get history of all healing actions"""
    db = get_db()
    logs = await db["healing_logs"].find().sort("timestamp", -1).limit(limit).to_list(limit)
    return {"status": "ok", "count": len(logs), "data": logs}

"""Alerts API routes"""
from fastapi import APIRouter
from services.db import get_db
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_alerts(status: str = None, limit: int = 50):
    """Get all alerts, optionally filtered by status"""
    db = get_db()
    query = {"status": status} if status else {}
    alerts = await db["alerts"].find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"status": "ok", "count": len(alerts), "data": alerts}

@router.post("/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged"""
    db = get_db()
    result = await db["alerts"].update_one(
        {"_id": alert_id},
        {"$set": {"status": "acknowledged", "ack_time": datetime.utcnow().isoformat()}}
    )
    return {"status": "ok", "modified": result.modified_count}

"""AutoHealOps - FastAPI Backend Server"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import json
import uvicorn
from datetime import datetime

from routes import metrics_router, alerts_router, heal_router, auth_router
from services.websocket_manager import ConnectionManager
from services.db import connect_db

app = FastAPI(
    title="AutoHealOps API",
    description="AI-Powered Self-Healing Kubernetes Backend",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

@app.on_event("startup")
async def startup():
    await connect_db()
    print("🚀 AutoHealOps Backend started on http://localhost:8000")

@app.get("/")
def root():
    return {"status": "ok", "service": "AutoHealOps Backend", "version": "1.0.0"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Push live metrics every 5 seconds
            await asyncio.sleep(5)
            data = {"type": "metrics_update", "timestamp": datetime.utcnow().isoformat()}
            await manager.broadcast(json.dumps(data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Register routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(heal_router, prefix="/heal", tags=["Self-Healing"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

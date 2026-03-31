"""MongoDB connection service"""
import motor.motor_asyncio
import os

client = None
db_instance = None

async def connect_db():
    global client, db_instance
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/autohealops")
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db_instance = client["autohealops"]
    print(f"✅ MongoDB connected: {uri}")

def get_db():
    return db_instance

"""Bounded JSON records with stable string IDs, SQLite demo or Mongo live."""

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path


class Store:
    def __init__(self, settings):
        self.lock = threading.RLock()
        self.days = settings.retention_days
        self.mongo = None
        if settings.mongo_uri:
            from pymongo import MongoClient

            self.mongo = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
            self.mongo.admin.command("ping")
            self.collection = self.mongo.autohealops.records
            self.collection.create_index([("kind", 1), ("id", 1)], unique=True)
            self.collection.create_index("expires_at", expireAfterSeconds=0)
            self.collection.create_index([("kind", 1), ("timestamp", -1)])
        else:
            Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, timestamp TEXT, body TEXT, PRIMARY KEY(kind,id))"
            )
            self.db.execute("CREATE INDEX IF NOT EXISTS record_time ON records(kind,timestamp)")

    def put(self, kind, item):
        with self.lock:
            if self.mongo:
                self.collection.replace_one(
                    {"kind": kind, "id": item["id"]},
                    {
                        "kind": kind,
                        **item,
                        "expires_at": datetime.fromisoformat(item["timestamp"])
                        + timedelta(days=self.days),
                    },
                    upsert=True,
                )
            else:
                self.db.execute(
                    "INSERT OR REPLACE INTO records VALUES (?,?,?,?)",
                    (kind, item["id"], item["timestamp"], json.dumps(item, allow_nan=False)),
                )
                self.db.commit()
        return item

    def list(self, kind):
        with self.lock:
            if self.mongo:
                return [
                    {k: v for k, v in row.items() if k not in ("_id", "expires_at", "kind")}
                    for row in self.collection.find({"kind": kind})
                    .sort("timestamp", -1)
                    .limit(1000)
                ]
            rows = self.db.execute(
                "SELECT body FROM records WHERE kind=? ORDER BY timestamp DESC LIMIT 1000", (kind,)
            ).fetchall()
            return [json.loads(row[0]) for row in rows]

    def get(self, kind, record_id):
        return next((row for row in self.list(kind) if row["id"] == record_id), None)

    def prune(self):
        with self.lock:
            if not self.mongo:
                cutoff = (datetime.now(UTC) - timedelta(days=self.days)).isoformat()
                self.db.execute("DELETE FROM records WHERE timestamp < ?", (cutoff,))
                self.db.execute(
                    "DELETE FROM records WHERE rowid NOT IN (SELECT rowid FROM records ORDER BY timestamp DESC LIMIT 20000)"
                )
                self.db.commit()

    def ping(self):
        if self.mongo:
            self.mongo.admin.command("ping")
        else:
            self.db.execute("SELECT 1")

    def close(self):
        self.mongo.close() if self.mongo else self.db.close()

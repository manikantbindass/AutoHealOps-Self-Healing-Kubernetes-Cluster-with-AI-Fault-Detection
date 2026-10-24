"""Validated configuration; no production credential defaults."""

import os
import secrets
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, model_validator


class Settings(BaseModel):
    mode: Literal["demo", "live"] = "demo"
    environment: Literal["development", "production"] = "development"
    jwt_secret: str = ""
    admin_password: str = ""
    viewer_password: str = ""
    origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    sqlite_path: str = "data/autohealops.sqlite"
    mongo_uri: str = ""
    ai_url: str = "http://127.0.0.1:8001"
    prometheus_url: str = "http://127.0.0.1:9090"
    namespace: str = Field(default="autohealops", pattern=r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$")
    healing_mode: Literal["recommendation", "manual", "automatic"] = "manual"
    dry_run: bool = True
    allow_automatic: bool = False
    max_replicas: int = Field(default=5, ge=1, le=20)
    cooldown_seconds: int = Field(default=300, ge=1)
    poll_seconds: int = Field(default=5, ge=1, le=300)
    retention_days: int = Field(default=7, ge=1, le=90)

    @model_validator(mode="after")
    def secure(self):
        if not self.origins:
            raise ValueError("At least one explicit browser Origin is required")
        for origin in self.origins:
            url = urlsplit(origin)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username
                or url.password
                or url.path
                or url.query
                or url.fragment
                or "*" in origin
            ):
                raise ValueError(
                    "ORIGINS must contain explicit HTTP(S) origins without paths or wildcards"
                )
        if self.environment == "production" or self.mode == "live":
            if len(self.jwt_secret) < 32 or self.jwt_secret.startswith("change-"):
                raise ValueError("JWT_SECRET must contain at least 32 random characters")
            if self.viewer_password and len(self.viewer_password) < 16:
                raise ValueError(
                    "VIEWER_PASSWORD must contain at least 16 characters when configured"
                )
            if len(self.admin_password) < 16:
                raise ValueError("ADMIN_PASSWORD must contain at least 16 characters")
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
        if self.mode == "live" and not self.mongo_uri:
            raise ValueError("Live mode requires MONGO_URI; SQLite is demo-only")
        if self.healing_mode == "automatic" and not self.allow_automatic:
            raise ValueError("Automatic healing requires ALLOW_AUTOMATIC=true")
        return self

    @classmethod
    def from_env(cls):
        values = {
            key: os.environ[key.upper()] for key in cls.model_fields if key.upper() in os.environ
        }
        if "origins" in values:
            values["origins"] = [x.strip() for x in values["origins"].split(",") if x.strip()]
        return cls(**values)

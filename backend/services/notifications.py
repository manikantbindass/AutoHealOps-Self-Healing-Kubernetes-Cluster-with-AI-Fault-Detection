"""Optional notification adapters. Destinations are startup-only secret configuration."""

import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit

import certifi
import httpx

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class Notifications:
    def __init__(self):
        self.webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        if self.webhook:
            url = urlsplit(self.webhook)
            if (
                url.scheme != "https"
                or url.hostname != "hooks.slack.com"
                or url.username
                or url.password
                or url.port not in (None, 443)
                or not url.path.startswith("/services/")
            ):
                raise ValueError(
                    "Slack webhook must be an HTTPS hooks.slack.com/services destination"
                )
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        if not 1 <= self.port <= 65535:
            raise ValueError("Invalid SMTP port")
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.sender = os.getenv("EMAIL_FROM", "")
        self.recipient = os.getenv("EMAIL_TO", "")
        self.last = {
            "slack": "configured; not yet sent" if self.webhook else "not configured",
            "email": "configured; not yet sent"
            if all([self.host, self.sender, self.recipient])
            else "not configured",
        }
        for value in (self.sender, self.recipient):
            if "\n" in value or "\r" in value:
                raise ValueError("Invalid notification email header")

    def email(self, text):
        message = EmailMessage()
        message["Subject"] = "AutoHealOps: fault detected"
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content(text)
        with smtplib.SMTP(self.host, self.port, timeout=5) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context(cafile=certifi.where()))
            smtp.ehlo()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(message)

    async def send(self, text):
        if self.webhook:
            try:
                async with httpx.AsyncClient(
                    timeout=5, trust_env=False, verify=SSL_CONTEXT
                ) as client:
                    response = await client.post(self.webhook, json={"text": text})
                    response.raise_for_status()
                self.last["slack"] = "delivered"
            except Exception:
                self.last["slack"] = "delivery failed; inspect destination configuration"
        if all([self.host, self.sender, self.recipient]):
            try:
                await asyncio.to_thread(self.email, text)
                self.last["email"] = "delivered"
            except Exception:
                self.last["email"] = "delivery failed; inspect SMTP configuration"
        return self.last

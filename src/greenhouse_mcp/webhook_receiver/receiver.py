"""FastAPI webhook receiver with HMAC verification and event routing."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request, Response

from greenhouse_mcp.webhook_receiver.models import WebhookDB

logger = logging.getLogger(__name__)

app = FastAPI(title="Greenhouse Webhook Receiver")

_db: WebhookDB | None = None


def get_db() -> WebhookDB:
    global _db
    if _db is None:
        db_path = os.environ.get(
            "WEBHOOK_DB_PATH",
            str(Path.home() / ".open-greenhouse-mcp" / "webhooks.db"),
        )
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = WebhookDB(db_path)
    return _db


def verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify Greenhouse HMAC-SHA256 signature."""
    if not signature_header.startswith("sha256 "):
        return False
    expected = signature_header[7:]  # strip "sha256 "
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)


async def execute_action(rule: dict[str, Any], payload: dict[str, Any]) -> None:
    """Execute the action defined in a routing rule."""
    action_type = rule["action_type"]
    raw = rule["action_config"]
    action_config = json.loads(raw) if isinstance(raw, str) else raw

    if action_type == "forward":
        url = action_config.get("url")
        if url:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, timeout=10.0)
                    if resp.status_code >= 400:
                        logger.error("Webhook forward to %s returned %d", url, resp.status_code)
            except Exception:
                logger.exception("Webhook forward to %s failed", url)
    elif action_type == "log":
        pass  # Already logged in the events table


@app.post("/webhooks/greenhouse")
async def receive_webhook(
    request: Request,
    signature: str = Header(None, alias="Signature"),
) -> Response:
    """Receive and process a Greenhouse webhook."""
    db = get_db()
    body = await request.body()

    # Verify signature
    secret = db.get_secret()
    if secret:
        if not signature:
            return Response(status_code=401, content="Missing signature")
        if not verify_signature(body, signature, secret):
            return Response(status_code=401, content="Invalid signature")

    # Parse payload
    payload = json.loads(body)
    event_type = payload.get("action", "unknown")

    # Log the event
    db.log_event(event_type=event_type, payload=payload)

    # Find and execute matching rules
    rules = db.get_matching_rules(event_type)
    for rule in rules:
        await execute_action(rule, payload)

    return Response(status_code=200, content="OK")


def main() -> None:
    """CLI entry point for the webhook receiver."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

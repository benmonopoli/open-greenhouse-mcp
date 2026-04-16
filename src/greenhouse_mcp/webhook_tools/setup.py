"""MCP tool for generating Greenhouse webhook setup instructions."""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_setup_guide(
    db: WebhookDB,
    *,
    receiver_url: Annotated[str, Field(description="Public URL where the webhook receiver is hosted")],
    events: Annotated[list[str] | None, Field(description="Event types to subscribe to — omit for all events")] = None,
) -> dict[str, Any]:
    """Generate webhook configuration instructions for Greenhouse. Read-only.

    Produces the exact values to enter in Greenhouse UI (Configure > Dev Center
    > Webhooks) and stores the generated secret key in the local database.
    """
    secret_key = secrets.token_hex(32)
    db.store_secret(secret_key)

    webhook_url = f"{receiver_url.rstrip('/')}/webhooks/greenhouse"

    if events is None:
        events = ["*"]  # subscribe to all

    return {
        "setup_instructions": {
            "step_1": "Go to Greenhouse > Configure > Dev Center > Webhooks",
            "step_2": "Click 'Create New Webhook'",
            "step_3_name": "Give it a name (e.g., 'MCP Webhook Receiver')",
            "step_4_url": f"Set the Endpoint URL to: {webhook_url}",
            "step_5_secret": f"Set the Secret Key to: {secret_key}",
            "step_6_events": (
                f"Subscribe to events: "
                f"{', '.join(events) if events != ['*'] else 'All events'}"
            ),
            "step_7": "Click 'Create Webhook' — Greenhouse will ping the URL to verify",
        },
        "values_to_copy": {
            "endpoint_url": webhook_url,
            "secret_key": secret_key,
            "events": events,
        },
        "note": "The secret key has been stored in the webhook database. "
        "Make sure the receiver is running before creating the webhook in Greenhouse.",
    }

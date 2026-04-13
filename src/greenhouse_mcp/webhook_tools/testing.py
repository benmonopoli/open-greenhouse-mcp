"""MCP tool for testing webhook rules."""

from __future__ import annotations

import json
from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_test_rule(
    db: WebhookDB, *, rule_id: int
) -> dict[str, Any]:
    """Dry-run a rule against the most recent matching event. Shows what would happen."""
    rules = db.list_rules()
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if not rule:
        return {"error": f"Rule {rule_id} not found"}

    events = db.list_recent_events(limit=100)
    matching_event = None
    for event in events:
        if rule["event_type"] == "*" or event["event_type"] == rule["event_type"]:
            matching_event = event
            break

    if not matching_event:
        return {"error": f"No recent events matching event_type '{rule['event_type']}'"}

    raw = rule["action_config"]
    action_config = json.loads(raw) if isinstance(raw, str) else raw

    return {
        "rule": rule,
        "matched_event": matching_event,
        "would_execute": {
            "action_type": rule["action_type"],
            "action_config": action_config,
        },
        "dry_run": True,
    }

"""MCP tools for managing webhook routing rules."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_list_rules(db: WebhookDB) -> dict[str, Any]:
    """List all webhook routing rules."""
    rules = db.list_rules()
    return {"rules": rules, "total": len(rules)}


async def webhook_create_rule(
    db: WebhookDB,
    *,
    event_type: str,
    action_type: str,
    action_url: str | None = None,
    filter_field: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    """Create a webhook routing rule. event_type can be a specific event or '*' for all.
    action_type is 'forward' (requires action_url) or 'log'."""
    action_config: dict[str, Any] = {}
    if action_url:
        action_config["url"] = action_url

    filter_config: dict[str, Any] = {}
    if filter_field and filter_value:
        filter_config[filter_field] = filter_value

    rule_id = db.create_rule(
        event_type=event_type,
        action_type=action_type,
        action_config=action_config,
        filter_config=filter_config,
    )
    return {"rule_id": rule_id, "status": "created"}


async def webhook_update_rule(
    db: WebhookDB,
    *,
    rule_id: int,
    event_type: str | None = None,
    action_type: str | None = None,
    action_url: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    """Update an existing webhook routing rule."""
    action_config = {"url": action_url} if action_url else None
    db.update_rule(
        rule_id,
        event_type=event_type,
        action_type=action_type,
        action_config=action_config,
        active=active,
    )
    return {"rule_id": rule_id, "status": "updated"}


async def webhook_delete_rule(
    db: WebhookDB, *, rule_id: int
) -> dict[str, Any]:
    """Delete a webhook routing rule."""
    db.delete_rule(rule_id)
    return {"rule_id": rule_id, "status": "deleted"}

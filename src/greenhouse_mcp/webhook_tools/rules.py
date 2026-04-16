"""MCP tools for managing webhook routing rules."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_list_rules(db: WebhookDB) -> dict[str, Any]:
    """List all webhook routing rules. Read-only.

    Returns all configured rules with their event types, actions, and status.
    """
    rules = db.list_rules()
    return {"rules": rules, "total": len(rules)}


async def webhook_create_rule(
    db: WebhookDB,
    *,
    event_type: Annotated[str, Field(description="Greenhouse event type or '*' for all — see webhook_list_events")],
    action_type: Annotated[str, Field(description="'forward' (requires action_url) or 'log'")],
    action_url: Annotated[str | None, Field(description="URL to forward events to (required if action_type='forward')")] = None,
    filter_field: Annotated[str | None, Field(description="JSON field to filter on (e.g., 'application.job.id')")] = None,
    filter_value: Annotated[str | None, Field(description="Required value for the filter field")] = None,
) -> dict[str, Any]:
    """Create a webhook routing rule. Write operation.

    Use webhook_list_events to see available event types. Set event_type
    to '*' to match all events, or a specific type like
    'candidate_stage_change'. Use webhook_test_rule to dry-run after creating.
    """
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
    rule_id: Annotated[int, Field(description="Rule ID — from webhook_list_rules")],
    event_type: Annotated[str | None, Field(description="New event type or '*'")] = None,
    action_type: Annotated[str | None, Field(description="'forward' or 'log'")] = None,
    action_url: Annotated[str | None, Field(description="New forward URL")] = None,
    active: Annotated[bool | None, Field(description="Enable or disable the rule")] = None,
) -> dict[str, Any]:
    """Update a webhook routing rule. Write operation.

    To find rule_id: webhook_list_rules.
    """
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
    db: WebhookDB,
    *,
    rule_id: Annotated[int, Field(description="Rule ID — from webhook_list_rules")],
) -> dict[str, Any]:
    """Delete a webhook routing rule. Write operation.

    To find rule_id: webhook_list_rules.
    """
    db.delete_rule(rule_id)
    return {"rule_id": rule_id, "status": "deleted"}

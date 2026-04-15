"""Harvest API — Email Templates tools (2 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_email_templates(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all email templates available in the organization. Read-only. Uses cached data.

    Email template IDs are used in reject_application (rejection_email.email_template_id)
    to send formatted rejection emails. Pass force_refresh=true after template changes.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/email_templates", params=params, force_refresh=force_refresh
    )


async def get_email_template(
    client: GreenhouseClient,
    *,
    email_template_id: Annotated[int, Field(description="Email template ID — get from list_email_templates")],
) -> dict[str, Any]:
    """Get a single email template by ID. Read-only. Returns the template name,
    body, and type.

    Use list_email_templates to find template IDs. Templates are used with
    reject_application for sending formatted rejection emails.
    """
    return await client.harvest_get_one(f"/email_templates/{email_template_id}")

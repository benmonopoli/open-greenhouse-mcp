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
    """List all email templates. Read-only.

    Resolves template names to IDs. When a user wants to send a rejection
    email, use this to find the template ID for reject_application's
    rejection_email parameter.
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
    """Get an email template by ID. Read-only.

    Returns template name, body, and type. To find template_id:
    list_email_templates → match by name.
    """
    return await client.harvest_get_one(f"/email_templates/{email_template_id}")

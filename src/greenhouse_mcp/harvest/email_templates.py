"""Harvest API — Email Templates tools (2 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_email_templates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all email templates available in the organization."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/email_templates", params=params, force_refresh=force_refresh
    )


async def get_email_template(
    client: GreenhouseClient,
    *,
    email_template_id: int,
) -> dict[str, Any]:
    """Get a single email template by ID."""
    return await client.harvest_get_one(f"/email_templates/{email_template_id}")

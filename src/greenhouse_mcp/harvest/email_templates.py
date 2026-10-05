"""Harvest API — Email Templates tools (2 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_email_templates(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    email_type: Annotated[
        str | None,
        Field(description="Filter by type, e.g. candidate_rejection, candidate_email"),
    ] = None,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all email templates. Read-only.

    Resolves template names to IDs. When a user wants to send a rejection
    email, use this (email_type='candidate_rejection') to find the template
    ID for reject_application's rejection_email parameter.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if email_type is not None:
        params["email_type"] = email_type
    return await client.harvest_get_cached(
        "/email_templates", params=params, force_refresh=force_refresh
    )


async def get_email_template(
    client: GreenhouseClient,
    *,
    email_template_id: Annotated[
        int, Field(description="Email template ID — get from list_email_templates")
    ],
) -> dict[str, Any]:
    """Get an email template by ID. Read-only.

    Returns template name, subject, body or html_body, email_type and
    sender settings. To find template_id: list_email_templates → match by name.
    """
    return await client.harvest_get_by_id("/email_templates", email_template_id)

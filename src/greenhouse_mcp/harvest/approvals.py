"""Harvest API — Approvals tools (6 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_approvals_for_job(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """List all approval flows for a job."""
    return await client.harvest_get(f"/jobs/{job_id}/approval_flows")


async def get_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_flow_id: int,
) -> dict[str, Any]:
    """Get a specific approval flow for a job."""
    return await client.harvest_get(f"/jobs/{job_id}/approval_flows/{approval_flow_id}")


async def request_approvals(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_flow_id: int,
) -> dict[str, Any]:
    """Trigger an approval request for a specific approval flow on a job."""
    return await client.harvest_post(
        f"/jobs/{job_id}/approval_flows/{approval_flow_id}/request_approvals"
    )


async def list_pending_approvals(
    client: GreenhouseClient,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    """List all pending approvals, optionally filtered by user_id."""
    params: dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    return await client.harvest_get("/approvals/pending", params=params or None)


async def replace_approver(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_flow_id: int,
    remove_user_id: int,
    add_user_id: int,
) -> dict[str, Any]:
    """Replace one approver with another in an approval flow."""
    json_data: dict[str, Any] = {
        "remove_user_id": remove_user_id,
        "add_user_id": add_user_id,
    }
    return await client.harvest_patch(
        f"/jobs/{job_id}/approval_flows/{approval_flow_id}/approvers", json_data=json_data
    )


async def create_or_replace_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_type: str,
    approver_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create or replace an approval flow for a job with type and approver groups."""
    json_data: dict[str, Any] = {
        "approval_type": approval_type,
        "approver_groups": approver_groups,
    }
    return await client.harvest_put(f"/jobs/{job_id}/approval_flows", json_data=json_data)

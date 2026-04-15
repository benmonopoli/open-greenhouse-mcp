"""Harvest API — Approvals tools (6 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_approvals_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List all approval flows for a job. Read-only.

    Returns configured approval workflows. To get details of a specific flow, use
    get_approval_flow. To trigger an approval request, use request_approvals.
    """
    return await client.harvest_get(f"/jobs/{job_id}/approval_flows")


async def get_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[int, Field(description="Approval flow ID — get from list_approvals_for_job")],
) -> dict[str, Any]:
    """Get a specific approval flow for a job. Read-only. Returns the flow type,
    approver groups, and current status.

    Use list_approvals_for_job to find flow IDs. To trigger an approval request,
    use request_approvals.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}/approval_flows/{approval_flow_id}")


async def request_approvals(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[int, Field(description="Approval flow ID to trigger — get from list_approvals_for_job")],
) -> dict[str, Any]:
    """Trigger an approval request for a specific approval flow on a job. Write operation.

    Sends notifications to approvers. To check pending approvals, use
    list_pending_approvals. To replace an approver, use replace_approver.
    """
    return await client.harvest_post(
        f"/jobs/{job_id}/approval_flows/{approval_flow_id}/request_approvals"
    )


async def list_pending_approvals(
    client: GreenhouseClient,
    *,
    user_id: Annotated[int | None, Field(description="Filter to approvals pending for this user — omit for all pending approvals")] = None,
) -> dict[str, Any]:
    """List all pending approvals across the organization. Read-only.

    Filter by user_id to see only a specific user's pending approvals. To trigger
    new approvals, use request_approvals. To replace an approver, use replace_approver.
    """
    params: dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    return await client.harvest_get("/approvals/pending", params=params or None)


async def replace_approver(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[int, Field(description="Approval flow ID")],
    remove_user_id: Annotated[int, Field(description="User ID to remove from the approver group")],
    add_user_id: Annotated[int, Field(description="User ID to add as replacement approver")],
) -> dict[str, Any]:
    """Replace one approver with another in an approval flow. Write operation.

    Swaps a single approver without changing the rest of the flow. To view
    the current flow, use get_approval_flow. To completely reconfigure a flow,
    use create_or_replace_approval_flow.
    """
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
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_type: Annotated[str, Field(description="Flow type: 'offer_candidate' or 'open_job'")],
    approver_groups: Annotated[list[dict[str, Any]], Field(description="Ordered list of approver groups: [{approvals_required: N, approvers: [{id: user_id}]}]")],
) -> dict[str, Any]:
    """Create or replace an entire approval flow for a job. Write operation — overwrites
    any existing flow of the same type.

    This replaces the full flow configuration. To swap a single approver without
    replacing the entire flow, use replace_approver instead. Get user IDs from list_users.
    """
    json_data: dict[str, Any] = {
        "approval_type": approval_type,
        "approver_groups": approver_groups,
    }
    return await client.harvest_put(f"/jobs/{job_id}/approval_flows", json_data=json_data)

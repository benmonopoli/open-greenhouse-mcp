"""Harvest API — Approvals tools (6 tools).

v3 splits an approval flow into three resources: ``approval_flows`` →
``approver_groups`` (one per step) → ``approvers`` (one per user). The read tools
reassemble them into the nested shape (flow → approver_groups → approvers).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def _user_names(client: GreenhouseClient, user_ids: list[int]) -> dict[Any, Any]:
    if not user_ids:
        return {}
    users = await client.harvest_get_ids("/users", "ids", user_ids)
    if client._is_error(users):
        return {}
    return {u.get("id"): u.get("name") for u in users.get("items", [])}


async def _expand_flows(
    client: GreenhouseClient, flows: list[dict[str, Any]]
) -> list[dict[str, Any]] | dict[str, Any]:
    """Nest approver groups and approvers (with user names) into each flow."""
    flow_ids = [f["id"] for f in flows if f.get("id") is not None]
    if not flow_ids:
        return flows
    groups = await client.harvest_get_ids("/approver_groups", "approval_flow_ids", flow_ids)
    if client._is_error(groups):
        return groups
    group_rows: list[dict[str, Any]] = groups.get("items", [])
    group_ids = [g["id"] for g in group_rows if g.get("id") is not None]
    approver_rows: list[dict[str, Any]] = []
    if group_ids:
        approvers = await client.harvest_get_ids("/approvers", "approver_group_ids", group_ids)
        if client._is_error(approvers):
            return approvers
        approver_rows = approvers.get("items", [])
    names = await _user_names(client, [a["user_id"] for a in approver_rows if a.get("user_id")])

    by_group: dict[Any, list[dict[str, Any]]] = {}
    for a in sorted(approver_rows, key=lambda r: r.get("sort_order") or 0):
        a["user_name"] = names.get(a.get("user_id"))
        by_group.setdefault(a.get("approver_group_id"), []).append(a)
    by_flow: dict[Any, list[dict[str, Any]]] = {}
    for g in sorted(group_rows, key=lambda r: r.get("sort_order") or 0):
        g["approvers"] = by_group.get(g.get("id"), [])
        by_flow.setdefault(g.get("approval_flow_id"), []).append(g)
    for f in flows:
        f["approver_groups"] = by_flow.get(f.get("id"), [])
    return flows


async def list_approvals_for_job(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """List approval flows for a job. Read-only.

    To find job_id: list_jobs → match by name. Each flow has approval_type
    (open_job, offer_job, offer_candidate), approval_status, sequential,
    requested_by_id, and `approver_groups` (ordered by sort_order), each with
    `approvers` (user_id, user_name, status: waiting/due/approved/rejected).
    """
    flows = await client.harvest_get(
        "/approval_flows", params={"job_ids": [job_id], "per_page": 500}, paginate="all"
    )
    if client._is_error(flows):
        return flows
    expanded = await _expand_flows(client, flows.get("items", []))
    if isinstance(expanded, dict):
        return expanded
    return {"items": expanded, "total": len(expanded)}


async def get_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[
        int, Field(description="Approval flow ID — get from list_approvals_for_job")
    ],
) -> dict[str, Any]:
    """Get a specific approval flow for a job. Read-only.

    Returns flow type, approval_status, and approver groups with their
    approvers. To find job_id: list_jobs → match by name. For
    approval_flow_id: list_approvals_for_job.
    """
    flow = await client.harvest_get_by_id("/approval_flows", approval_flow_id)
    if client._is_error(flow):
        return flow
    expanded = await _expand_flows(client, [flow])
    if isinstance(expanded, dict):
        return expanded
    return expanded[0]


async def request_approvals(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[
        int, Field(description="Approval flow ID to trigger — get from list_approvals_for_job")
    ],
) -> dict[str, Any]:
    """Trigger an approval request for a flow on a job. Write operation.

    Sends the approval request emails to the first approvers. To find job_id:
    list_jobs → match by name. For approval_flow_id: list_approvals_for_job.
    """
    return await client.harvest_post(f"/approval_flows/{approval_flow_id}/request_approvals")


async def list_pending_approvals(
    client: GreenhouseClient,
    *,
    user_id: Annotated[
        int | None,
        Field(
            description="Filter to approvals pending for this user — omit for all pending approvals"
        ),
    ] = None,
    include_waiting: Annotated[
        bool,
        Field(description="Also include approvers whose turn hasn't come yet (status 'waiting')"),
    ] = False,
) -> dict[str, Any]:
    """List all pending approvals for a user (or org-wide). Read-only.

    By default returns approvers whose decision is due now. Each item has
    approver_id, user_id, user_name, status, request_sent_at, job_id,
    offer_id, approval_type and approval_flow_id. To find user_id:
    list_users → match by name or email. Omit user_id to see all pending
    approvals across the organization.
    """
    approvers: list[dict[str, Any]] = []
    for status in ("due", "waiting") if include_waiting else ("due",):
        params: dict[str, Any] = {"status": status, "per_page": 500}
        if user_id is not None:
            params["user_ids"] = [user_id]
        result = await client.harvest_get("/approvers", params=params, paginate="all")
        if client._is_error(result):
            return result
        approvers.extend(result.get("items", []))

    group_ids = [a["approver_group_id"] for a in approvers if a.get("approver_group_id")]
    groups: dict[Any, dict[str, Any]] = {}
    if group_ids:
        res = await client.harvest_get_ids("/approver_groups", "ids", group_ids)
        if client._is_error(res):
            return res
        groups = {g.get("id"): g for g in res.get("items", [])}
    flow_ids = [g["approval_flow_id"] for g in groups.values() if g.get("approval_flow_id")]
    flows: dict[Any, dict[str, Any]] = {}
    if flow_ids:
        res = await client.harvest_get_ids("/approval_flows", "ids", flow_ids)
        if client._is_error(res):
            return res
        flows = {f.get("id"): f for f in res.get("items", [])}
    names = await _user_names(client, [a["user_id"] for a in approvers if a.get("user_id")])

    items = []
    for a in approvers:
        group = groups.get(a.get("approver_group_id"), {})
        flow = flows.get(group.get("approval_flow_id"), {})
        items.append({
            "approver_id": a.get("id"),
            "user_id": a.get("user_id"),
            "user_name": names.get(a.get("user_id")),
            "status": a.get("status"),
            "request_sent_at": a.get("request_sent_at"),
            "approver_group_id": a.get("approver_group_id"),
            "approval_flow_id": group.get("approval_flow_id"),
            "job_id": flow.get("job_id"),
            "offer_id": flow.get("offer_id"),
            "approval_type": flow.get("approval_type"),
            "approval_status": flow.get("approval_status"),
        })
    return {"items": items, "total": len(items)}


async def replace_approver(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_flow_id: Annotated[int, Field(description="Approval flow ID")],
    remove_user_id: Annotated[int, Field(description="User ID to remove from the approver group")],
    add_user_id: Annotated[int, Field(description="User ID to add as replacement approver")],
) -> dict[str, Any]:
    """Replace one approver with another in an approval flow. Write operation.

    Users say "swap John for Sarah on the Backend approval." For user IDs:
    list_users → match by name. For job_id: list_jobs. For approval_flow_id:
    list_approvals_for_job. The approver being removed must not have
    approved or rejected yet.
    """
    groups = await client.harvest_get(
        "/approver_groups", params={"approval_flow_ids": [approval_flow_id], "per_page": 500},
        paginate="all",
    )
    if client._is_error(groups):
        return groups
    group_ids = [g["id"] for g in groups.get("items", []) if g.get("id") is not None]
    if not group_ids:
        return {"error": f"Approval flow {approval_flow_id} has no approver groups.",
                "status_code": 404}
    approvers = await client.harvest_get(
        "/approvers",
        params={"approver_group_ids": group_ids, "user_ids": [remove_user_id], "per_page": 500},
        paginate="all",
    )
    if client._is_error(approvers):
        return approvers
    rows = approvers.get("items", [])
    open_rows = [a for a in rows if a.get("status") in ("waiting", "due")] or rows
    if not open_rows:
        return {"error": f"User {remove_user_id} is not an approver on flow {approval_flow_id}.",
                "status_code": 404}
    group_id = open_rows[0].get("approver_group_id")
    json_data: dict[str, Any] = {"remove_user_id": remove_user_id, "add_user_id": add_user_id}
    return await client.harvest_put(
        f"/approver_groups/{group_id}/replace_approver", json_data=json_data
    )


def _normalize_groups(approver_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept legacy approver entries ({id: user_id}) as well as {user_id|email|employee_id}."""
    out = []
    for group in approver_groups:
        approvers = []
        for a in group.get("approvers", []):
            if "id" in a and not any(k in a for k in ("user_id", "email", "employee_id")):
                approvers.append({"user_id": a["id"]})
            else:
                approvers.append(
                    {k: v for k, v in a.items() if k in ("user_id", "email", "employee_id")}
                )
        out.append({"approvals_required": group.get("approvals_required", 1),
                    "approvers": approvers})
    return out


async def create_or_replace_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    approval_type: Annotated[
        str, Field(description="Flow type: 'open_job', 'offer_job' or 'offer_candidate'")
    ],
    approver_groups: Annotated[
        list[dict[str, Any]],
        Field(
            description="Ordered approver groups: [{approvals_required: N, approvers: "
            "[{user_id: N} | {email: '...'}]}]"
        ),
    ],
    sequential: Annotated[
        bool, Field(description="Groups approve one after another (true) or all at once")
    ] = True,
) -> dict[str, Any]:
    """Create or replace an approval flow for a job. Write operation — overwrites existing.

    If the job already has a flow of this approval_type, its approver groups
    are replaced; otherwise a new flow is created (pending — call
    request_approvals to start it). To find job_id: list_jobs → match by
    name. For approver user IDs: list_users → match by name.
    """
    groups = _normalize_groups(approver_groups)
    existing = await client.harvest_get(
        "/approval_flows",
        params={"job_ids": [job_id], "approval_type": approval_type, "per_page": 500},
        paginate="all",
    )
    if client._is_error(existing):
        return existing
    flow = next((f for f in existing.get("items", []) if not f.get("offer_id")), None)
    if flow is None:
        json_data: dict[str, Any] = {
            "job_id": job_id,
            "approval_type": approval_type,
            "sequential": sequential,
            "approver_groups": groups,
        }
        return await client.harvest_post("/approval_flows", json_data=json_data)
    if flow.get("sequential") != sequential:
        patched = await client.harvest_patch(
            f"/approval_flows/{flow['id']}", json_data={"sequential": sequential}
        )
        if client._is_error(patched):
            return patched
    return await client.harvest_put(
        f"/approval_flows/{flow['id']}/replace_approver_groups",
        json_data={"approver_groups": groups},
    )

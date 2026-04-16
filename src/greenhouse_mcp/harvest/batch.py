"""Harvest API — Batch operation tools (3 tools).

Perform bulk actions on multiple candidates/applications in a single call.
Includes rate-limit-aware delays between operations.
"""
from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def bulk_reject(
    client: GreenhouseClient,
    *,
    application_ids: Annotated[list[int], Field(description="Application IDs to reject — get from list_applications or pipeline_summary")],
    rejection_reason_id: Annotated[int | None, Field(description="Rejection reason ID — get from list_rejection_reasons")] = None,
    rejection_email: Annotated[bool, Field(description="Send rejection email to each candidate")] = False,
) -> dict[str, Any]:
    """Reject multiple applications in one call. Write operation — rate-limited.

    Users say "reject everyone who's been inactive for 30 days on the Backend role."
    First use stale_applications to identify the targets, then pass their
    application_ids here. For rejection_reason_id: list_rejection_reasons →
    match by name. Processes sequentially with rate-limit delays.
    """
    if not application_ids:
        return {"error": "No application IDs provided.", "status_code": 0}

    successes: list[int] = []
    failures: list[dict[str, Any]] = []

    for app_id in application_ids:
        json_data: dict[str, Any] = {}
        if rejection_reason_id:
            json_data["rejection_reason_id"] = rejection_reason_id
        if rejection_email:
            json_data["send_rejection_email"] = True

        result = await client.harvest_post(
            f"/applications/{app_id}/reject",
            json_data=json_data if json_data else None,
        )
        if "error" in result and "status_code" in result:
            failures.append({
                "application_id": app_id,
                "error": result["error"],
            })
        else:
            successes.append(app_id)

        # Rate-limit delay (50 req/10s = 200ms between calls)
        await asyncio.sleep(0.25)

    return {
        "total": len(application_ids),
        "succeeded": len(successes),
        "failed": len(failures),
        "successful_ids": successes,
        "failures": failures,
    }


async def bulk_tag(
    client: GreenhouseClient,
    *,
    candidate_ids: Annotated[list[int], Field(description="Candidate IDs to tag — get from list_candidates or search")],
    tag_name: Annotated[str, Field(description="Tag name to apply — created on-the-fly if it doesn't exist")],
) -> dict[str, Any]:
    """Tag multiple candidates in one call. Write operation — rate-limited.

    Users say "tag all the candidates from the hiring event." Pass candidate_ids
    from search or pipeline tools and a tag_name (created automatically if new).
    Processes sequentially with rate-limit delays.
    """
    if not candidate_ids:
        return {"error": "No candidate IDs provided.", "status_code": 0}

    successes: list[int] = []
    failures: list[dict[str, Any]] = []

    for cid in candidate_ids:
        result = await client.harvest_put(
            f"/candidates/{cid}/tags",
            json_data={"tag": tag_name},
        )
        if "error" in result and "status_code" in result:
            failures.append({
                "candidate_id": cid,
                "error": result["error"],
            })
        else:
            successes.append(cid)

        await asyncio.sleep(0.25)

    return {
        "total": len(candidate_ids),
        "succeeded": len(successes),
        "failed": len(failures),
        "tag": tag_name,
        "successful_ids": successes,
        "failures": failures,
    }


async def bulk_advance(
    client: GreenhouseClient,
    *,
    application_ids: Annotated[list[int], Field(description="Application IDs to advance")],
    from_stage_id: Annotated[int | None, Field(description="Current stage ID — if omitted, each application advances from its current stage")] = None,
) -> dict[str, Any]:
    """Advance multiple applications to the next stage. Write operation — rate-limited.

    Users say "move everyone past phone screen forward." Get application_ids from
    pipeline_summary or list_applications. Optionally specify from_stage_id
    (list_job_stages_for_job → match by name) to only advance candidates in
    that specific stage. Processes sequentially with rate-limit delays.
    """
    if not application_ids:
        return {"error": "No application IDs provided.", "status_code": 0}

    successes: list[int] = []
    failures: list[dict[str, Any]] = []

    for app_id in application_ids:
        json_data: dict[str, Any] = {}
        if from_stage_id:
            json_data["from_stage_id"] = from_stage_id

        result = await client.harvest_post(
            f"/applications/{app_id}/advance",
            json_data=json_data if json_data else None,
        )
        if "error" in result and "status_code" in result:
            failures.append({
                "application_id": app_id,
                "error": result["error"],
            })
        else:
            successes.append(app_id)

        await asyncio.sleep(0.25)

    return {
        "total": len(application_ids),
        "succeeded": len(successes),
        "failed": len(failures),
        "successful_ids": successes,
        "failures": failures,
    }

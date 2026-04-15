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

    Use this for pipeline hygiene — e.g., bulk-reject 30 stale candidates after
    reviewing the output of stale_applications. Pass a list of application IDs.

    Optionally specify a rejection_reason_id (from list_rejection_reasons) and
    whether to send a rejection email. Processes sequentially with rate-limit
    delays to avoid hitting Greenhouse's 50 req/10s limit.

    Returns a summary of successes and failures.
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
    """Add a tag to multiple candidates in one call. Write operation — rate-limited.

    Use this to tag a batch of sourced candidates, mark candidates from a hiring
    event, or categorize candidates for reporting. Pass a list of candidate IDs
    and the tag name (will be created if it doesn't exist).

    Processes sequentially with rate-limit delays. Returns success/failure counts.
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
    """Advance multiple applications to the next stage in one call. Write operation — rate-limited.

    Use this to move a batch of candidates forward — e.g., all candidates who
    passed a phone screen. Optionally specify from_stage_id to only advance
    candidates currently in that specific stage (safety check).

    Processes sequentially with rate-limit delays. Returns success/failure counts.
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

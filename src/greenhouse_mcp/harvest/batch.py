"""Harvest API — Batch operation tools (3 tools).

Perform bulk actions on multiple candidates/applications in a single call.
Lookups are batched (one request per 50 ids); the writes themselves are one
request per record (Harvest v3 has no bulk endpoint for these), with
rate-limit-aware delays between them.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.harvest.workflows import _is_error

_WRITE_DELAY = 0.25  # seconds between writes


async def _fetch_tag_id(client: GreenhouseClient, tag_name: str) -> int | None | dict[str, Any]:
    """Find a candidate tag id by name (exact, then case-insensitive). None if absent."""
    result = await client.harvest_get("/candidate_tags", params={"per_page": 500}, paginate="all")
    if _is_error(result):
        return result
    tags = result.get("items", [])
    for tag in tags:
        if tag.get("name") == tag_name:
            return int(tag["id"])
    lowered = tag_name.lower()
    for tag in tags:
        if (tag.get("name") or "").lower() == lowered:
            return int(tag["id"])
    return None


async def bulk_reject(
    client: GreenhouseClient,
    *,
    application_ids: Annotated[
        list[int],
        Field(
            description="Application IDs to reject — get from list_applications or pipeline_summary"
        ),
    ],
    rejection_reason_id: Annotated[
        int, Field(description="Rejection reason ID (required) — get from list_rejection_reasons")
    ],
    rejection_email: Annotated[
        bool, Field(description="Send a rejection email to each candidate")
    ] = False,
    email_template_id: Annotated[
        int | None,
        Field(description="Rejection email template — list_email_templates → match by name"),
    ] = None,
    email_from_user_id: Annotated[
        int | None, Field(description="User the rejection email is sent from — list_users")
    ] = None,
    notes: Annotated[
        str | None, Field(description="Internal rejection notes (not sent to the candidate)")
    ] = None,
) -> dict[str, Any]:
    """Reject multiple applications in one call. Write operation — rate-limited.

    Users say "reject everyone who's been inactive for 30 days on the Backend role."
    First use stale_applications to identify the targets, then pass their
    application_ids here. rejection_reason_id is required: list_rejection_reasons
    → match by name. To email candidates, set rejection_email=true and pass
    email_template_id (list_email_templates). Processes sequentially with
    rate-limit delays.
    """
    if not application_ids:
        return {"error": "No application IDs provided.", "status_code": 0}

    json_data: dict[str, Any] = {"rejection_reason_id": rejection_reason_id}
    if notes:
        json_data["notes"] = notes
    if rejection_email:
        email: dict[str, Any] = {}
        if email_template_id is not None:
            email["email_template_id"] = email_template_id
        if email_from_user_id is not None:
            email["email_from_user_id"] = email_from_user_id
        json_data["rejection_email"] = email

    successes: list[int] = []
    failures: list[dict[str, Any]] = []
    for app_id in application_ids:
        result = await client.harvest_post(f"/applications/{app_id}/reject", json_data=json_data)
        if _is_error(result):
            failures.append(
                {"application_id": app_id, "error": result["error"], "detail": result.get("detail")}
            )
        else:
            successes.append(app_id)
        await asyncio.sleep(_WRITE_DELAY)

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
    candidate_ids: Annotated[
        list[int], Field(description="Candidate IDs to tag — get from list_candidates or search")
    ],
    tag_name: Annotated[
        str, Field(description="Tag name to apply — created on-the-fly if it doesn't exist")
    ],
) -> dict[str, Any]:
    """Tag multiple candidates in one call. Write operation — rate-limited.

    Users say "tag all the candidates from the hiring event." Pass candidate_ids
    from search or pipeline tools and a tag_name (created automatically if new).
    Candidates who already have the tag are skipped. Processes sequentially
    with rate-limit delays.
    """
    if not candidate_ids:
        return {"error": "No candidate IDs provided.", "status_code": 0}

    tag_id = await _fetch_tag_id(client, tag_name)
    if isinstance(tag_id, dict):
        return {"error": "Failed to look up candidate tags.", "detail": tag_id}
    tag_created = False
    if tag_id is None:
        created = await client.harvest_post("/candidate_tags", json_data={"name": tag_name})
        if _is_error(created) or "id" not in created:
            return {"error": f"Failed to create tag '{tag_name}'.", "detail": created}
        tag_id = int(created["id"])
        tag_created = True

    already: set[int] = set()
    if not tag_created:
        existing = await client.harvest_get_ids(
            "/applied_candidate_tags",
            "candidate_ids",
            candidate_ids,
            params={"candidate_tag_ids": [tag_id], "per_page": 500},
        )
        if not _is_error(existing):
            already = {
                r["candidate_id"]
                for r in existing.get("items", [])
                if r.get("candidate_tag_id") == tag_id
            }

    successes: list[int] = []
    skipped: list[int] = []
    failures: list[dict[str, Any]] = []
    for cid in candidate_ids:
        if cid in already:
            skipped.append(cid)
            continue
        result = await client.harvest_post(
            "/applied_candidate_tags",
            json_data={"candidate_id": cid, "candidate_tag_id": tag_id},
        )
        if _is_error(result):
            failures.append(
                {"candidate_id": cid, "error": result["error"], "detail": result.get("detail")}
            )
        else:
            successes.append(cid)
        await asyncio.sleep(_WRITE_DELAY)

    return {
        "total": len(candidate_ids),
        "succeeded": len(successes),
        "already_tagged": len(skipped),
        "failed": len(failures),
        "tag": tag_name,
        "tag_id": tag_id,
        "tag_created": tag_created,
        "successful_ids": successes,
        "already_tagged_ids": skipped,
        "failures": failures,
    }


async def bulk_advance(
    client: GreenhouseClient,
    *,
    application_ids: Annotated[list[int], Field(description="Application IDs to advance")],
    from_stage_id: Annotated[
        int | None,
        Field(
            description="Only advance apps currently in this job interview stage "
            "(list_job_stages_for_job → match by name); omit to advance each from its "
            "current stage"
        ),
    ] = None,
) -> dict[str, Any]:
    """Advance multiple applications to the next stage. Write operation — rate-limited.

    Users say "move everyone past phone screen forward." Get application_ids from
    pipeline_summary or list_applications. Each application moves from its
    current stage to the next one on its job's interview plan. Optionally pass
    from_stage_id (list_job_stages_for_job → match by name) to only advance
    applications currently in that stage — others are skipped. Rejected, hired
    or prospect applications are skipped. Processes sequentially with
    rate-limit delays.
    """
    if not application_ids:
        return {"error": "No application IDs provided.", "status_code": 0}

    lookup = await client.harvest_get_ids(
        "/applications", "ids", application_ids, params={"per_page": 100}
    )
    if _is_error(lookup):
        return {"error": "Failed to look up the applications' current stages.", "detail": lookup}
    apps = {a["id"]: a for a in lookup.get("items", []) if "id" in a}

    successes: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for app_id in application_ids:
        app = apps.get(app_id)
        if app is None:
            failures.append({"application_id": app_id, "error": "Application not found."})
            continue
        current = app.get("job_interview_stage_id")
        if app.get("status") != "in_process" or current is None:
            skipped.append(
                {
                    "application_id": app_id,
                    "reason": f"not active in a job stage (status: {app.get('status')})",
                }
            )
            continue
        if from_stage_id is not None and current != from_stage_id:
            skipped.append(
                {
                    "application_id": app_id,
                    "reason": f"in stage '{app.get('stage_name')}' ({current}), "
                    f"not {from_stage_id}",
                }
            )
            continue

        result = await client.harvest_post(
            f"/applications/{app_id}/move", json_data={"from_stage_id": current}
        )
        if _is_error(result):
            failures.append(
                {"application_id": app_id, "error": result["error"], "detail": result.get("detail")}
            )
        else:
            successes.append(
                {"application_id": app_id, "from_stage": app.get("stage_name"),
                 "from_stage_id": current}
            )
        await asyncio.sleep(_WRITE_DELAY)

    return {
        "total": len(application_ids),
        "succeeded": len(successes),
        "skipped": len(skipped),
        "failed": len(failures),
        "successful_ids": [s["application_id"] for s in successes],
        "advanced": successes,
        "skipped_details": skipped,
        "failures": failures,
    }

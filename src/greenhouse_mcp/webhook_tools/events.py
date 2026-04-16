"""MCP tools for listing webhook events."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.webhook_receiver.models import WebhookDB

WEBHOOK_EVENT_TYPES = {
    "new_candidate_application": "A new application is created",
    "delete_application": "An application is deleted",
    "application_updated": "An application is updated",
    "offer_created": "An offer is created",
    "offer_approved": "An offer is approved",
    "offer_updated": "An offer is updated",
    "offer_deleted": "An offer is deleted",
    "new_prospect_application": "A new prospect is created",
    "delete_candidate": "A candidate is deleted",
    "hire_candidate": "A candidate is hired",
    "merge_candidate": "Two candidates are merged",
    "candidate_stage_change": "A candidate moves to a new stage",
    "unhire_candidate": "A hire is reverted",
    "reject_candidate": "A candidate is rejected",
    "unreject_candidate": "A rejection is reverted",
    "update_candidate": "A candidate profile is updated",
    "candidate_anonymized": "A candidate is anonymized (GDPR)",
    "interview_deleted": "A scheduled interview is deleted",
    "scorecard_deleted": "A scorecard is deleted",
    "job_created": "A new job is created",
    "job_deleted": "A job is deleted",
    "job_updated": "A job is updated",
    "job_approved": "A job is approved",
    "job_post_created": "A job post is created",
    "job_post_updated": "A job post is updated",
    "job_post_deleted": "A job post is deleted",
    "job_interview_stage_deleted": "A job stage is deleted",
    "department_deleted": "A department is deleted",
    "office_deleted": "An office is deleted",
}


async def webhook_list_events() -> dict[str, Any]:
    """List all Greenhouse webhook event types with descriptions. Read-only.

    Reference for webhook_create_rule — shows available event types like
    'candidate_stage_change', 'hire_candidate', 'new_candidate_application', etc.
    """
    return {
        "events": [{"event_type": k, "description": v} for k, v in WEBHOOK_EVENT_TYPES.items()],
        "total": len(WEBHOOK_EVENT_TYPES),
    }


async def webhook_list_recent(
    db: WebhookDB,
    *,
    limit: Annotated[int, Field(description="Maximum events to return")] = 50,
) -> dict[str, Any]:
    """List recent webhook events received by the receiver. Read-only.

    Shows the latest events captured by the webhook receiver, useful for
    debugging and verifying webhook delivery.
    """
    events = db.list_recent_events(limit=limit)
    return {"events": events, "total": len(events)}

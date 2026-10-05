"""Tests for harvest/applications.py (Harvest v3)."""
from __future__ import annotations

import json

import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient
from tests.conftest import HARVEST_BASE, make_client


def _app(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": 1,
        "candidate_id": 10,
        "job_id": 100,
        "stage_id": 9001,
        "job_interview_stage_id": 555,
        "stage_name": "Phone Screen",
        "status": "in_process",
        "prospect": False,
        "created_at": "2026-09-01T00:00:00Z",
        "last_activity_at": "2026-09-02T00:00:00Z",
    }
    base.update(kw)
    return base


def _is_write_tool(fn: object) -> bool:
    """Mirror of server._is_write_tool (importing server builds every module's tools)."""
    import inspect

    source = inspect.getsource(fn)  # type: ignore[arg-type]
    return any(
        m in source
        for m in ("harvest_post", "harvest_patch", "harvest_put", "harvest_delete")
    )


def _body(route: respx.Route, n: int = -1) -> dict[str, object]:
    return json.loads(route.calls[n].request.content)  # type: ignore[no-any-return]


@respx.mock
async def test_list_applications(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    apps = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200,
            json=[_app()],
            headers={"link": f'<{HARVEST_BASE}/applications?cursor=abc>; rel="next"'},
        )
    )
    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 100, "name": "Backend Engineer"}])
    )
    result = await list_applications(client)
    assert result["items"][0]["job_name"] == "Backend Engineer"
    assert result["has_next"] is True
    assert result["next_cursor"] == "abc"
    assert apps.calls[0].request.url.params["per_page"] == "500"


@respx.mock
async def test_list_applications_filters_are_v3(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await list_applications(
        client,
        job_id=100,
        candidate_id=10,
        status="rejected",
        created_after="2026-01-01T00:00:00Z",
        created_before="2026-02-01T00:00:00Z",
        last_activity_after="2026-01-15T00:00:00Z",
    )
    assert result["items"] == []
    params = route.calls[0].request.url.params
    assert params["job_ids"] == "100"
    assert params["candidate_ids"] == "10"
    assert params["status"] == "rejected"
    assert params["created_at[gte]"] == "2026-01-01T00:00:00Z"
    assert params["created_at[lt]"] == "2026-02-01T00:00:00Z"
    assert params["last_activity_at[gt]"] == "2026-01-15T00:00:00Z"
    assert "job_id" not in params and "page" not in params


@respx.mock
async def test_list_applications_cursor_drops_other_params(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    route = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[])
    )
    await list_applications(client, cursor="xyz", job_id=100)
    assert dict(route.calls[0].request.url.params) == {"cursor": "xyz"}


@respx.mock
async def test_list_applications_job_lookup_failure_warns(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_app()])
    )
    respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(403, json={}))
    result = await list_applications(client)
    assert result["items"][0]["job_name"] is None
    assert "warnings" in result


@respx.mock
async def test_list_applications_error(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(422, json={"message": "bad"})
    )
    result = await list_applications(client, job_id=1)
    assert result["status_code"] == 422


@respx.mock
async def test_get_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import get_application

    apps = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_app(id=42)])
    )
    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 100, "name": "Backend Engineer"}])
    )
    atts = respx.get(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(
            200, json=[{"id": 7, "application_id": 42, "type": "resume", "url": "https://x"}]
        )
    )
    result = await get_application(client, application_id=42)
    assert result["id"] == 42
    assert result["job_name"] == "Backend Engineer"
    assert result["attachments"][0]["type"] == "resume"
    assert apps.calls[0].request.url.params["ids"] == "42"
    assert atts.calls[0].request.url.params["application_ids"] == "42"


@respx.mock
async def test_get_application_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import get_application

    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))
    result = await get_application(client, application_id=9999)
    assert result["status_code"] == 404


@respx.mock
async def test_create_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import create_application

    route = respx.post(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(201, json=_app(id=5, job_id=200))
    )
    result = await create_application(
        client, candidate_id=10, job_id=200, source_id=3, referrer_id=4, initial_stage_id=6
    )
    assert result["id"] == 5
    assert _body(route) == {
        "candidate_id": 10,
        "job_id": 200,
        "source_id": 3,
        "referrer_id": 4,
        "initial_stage_id": 6,
    }


@respx.mock
async def test_create_application_uploads_attachments(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import create_application

    respx.post(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(201, json=_app(id=5))
    )
    att = respx.post(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(201, json={"id": 77, "application_id": 5})
    )
    result = await create_application(
        client,
        candidate_id=10,
        job_id=100,
        attachments=[
            {"filename": "cv.pdf", "type": "resume", "content": "QUJD"},
            {"filename": "bad.pdf", "type": "resume"},
        ],
    )
    assert result["attachment_results"][0]["id"] == 77
    assert result["attachment_results"][1]["status_code"] == 400
    assert _body(att) == {
        "application_id": 5,
        "filename": "cv.pdf",
        "type": "resume",
        "content": "QUJD",
    }


@respx.mock
async def test_update_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import update_application

    route = respx.patch(f"{HARVEST_BASE}/applications/42").mock(
        return_value=httpx.Response(200, json=_app(id=42, source_id=7))
    )
    result = await update_application(
        client, application_id=42, source_id=7, custom_fields=[{"id": 11, "value": "x"}]
    )
    assert result["source_id"] == 7
    assert _body(route) == {
        "source_id": 7,
        "custom_fields": [{"custom_field_id": 11, "value": "x"}],
    }


@respx.mock
async def test_delete_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import delete_application

    respx.delete(f"{HARVEST_BASE}/applications/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "message": "deleted"})
    )
    result = await delete_application(client, application_id=42)
    assert result["id"] == 42


@respx.mock
async def test_advance_application_with_explicit_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import advance_application

    route = respx.post(f"{HARVEST_BASE}/applications/42/move").mock(
        return_value=httpx.Response(204)
    )
    result = await advance_application(client, application_id=42, from_stage_id=555)
    assert result == {"success": True, "application_id": 42, "from_stage_id": 555}
    assert _body(route) == {"from_stage_id": 555}


@respx.mock
async def test_advance_application_resolves_current_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import advance_application

    lookup = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_app(id=42, job_interview_stage_id=555)])
    )
    route = respx.post(f"{HARVEST_BASE}/applications/42/move").mock(
        return_value=httpx.Response(204)
    )
    result = await advance_application(client, application_id=42)
    assert result["success"] is True
    assert lookup.calls[0].request.url.params["ids"] == "42"
    # from_stage_id is the job interview stage, not the application-stage row id
    assert _body(route) == {"from_stage_id": 555}


@respx.mock
async def test_advance_application_no_current_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import advance_application

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200, json=[_app(id=42, job_interview_stage_id=None, status="rejected")]
        )
    )
    move = respx.post(f"{HARVEST_BASE}/applications/42/move")
    result = await advance_application(client, application_id=42)
    assert result["status_code"] == 400
    assert not move.called


@respx.mock
async def test_move_application_to_other_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import move_application

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[_app(id=42)])
    )
    route = respx.post(f"{HARVEST_BASE}/applications/42/move").mock(
        return_value=httpx.Response(204)
    )
    result = await move_application(client, application_id=42, new_job_id=200, new_stage_id=9)
    assert result["success"] is True
    assert _body(route) == {"from_stage_id": 555, "to_stage_id": 9, "to_job_id": 200}


@respx.mock
async def test_move_application_same_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import move_application_same_job

    route = respx.post(f"{HARVEST_BASE}/applications/42/move").mock(
        return_value=httpx.Response(204)
    )
    result = await move_application_same_job(
        client, application_id=42, from_stage_id=1, to_stage_id=2
    )
    assert result["success"] is True
    assert _body(route) == {"from_stage_id": 1, "to_stage_id": 2}


@respx.mock
async def test_move_stale_stage_error_passes_through(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import move_application_same_job

    respx.post(f"{HARVEST_BASE}/applications/42/move").mock(
        return_value=httpx.Response(422, json={"message": "from_stage_id mismatch"})
    )
    result = await move_application_same_job(
        client, application_id=42, from_stage_id=1, to_stage_id=2
    )
    assert result["status_code"] == 422


@respx.mock
async def test_reject_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import reject_application

    route = respx.post(f"{HARVEST_BASE}/applications/42/reject").mock(
        return_value=httpx.Response(204)
    )
    result = await reject_application(
        client,
        application_id=42,
        rejection_reason_id=3,
        notes="Not a fit",
        rejection_email={"email_template_id": 8, "email_from_user_id": 2},
    )
    assert result == {"success": True, "application_id": 42, "status": "rejected"}
    assert _body(route) == {
        "rejection_reason_id": 3,
        "notes": "Not a fit",
        "rejection_email": {"email_template_id": 8, "email_from_user_id": 2},
    }


@respx.mock
async def test_reject_application_defaults_email_sender() -> None:
    from greenhouse_mcp.harvest.applications import reject_application

    client = make_client(user_id="321")
    route = respx.post(f"{HARVEST_BASE}/applications/42/reject").mock(
        return_value=httpx.Response(204)
    )
    await reject_application(
        client, application_id=42, rejection_reason_id=3, rejection_email={"email_template_id": 8}
    )
    assert _body(route)["rejection_email"] == {"email_template_id": 8, "email_from_user_id": 321}


@respx.mock
async def test_unreject_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import unreject_application

    respx.post(f"{HARVEST_BASE}/applications/42/unreject").mock(
        return_value=httpx.Response(204)
    )
    result = await unreject_application(client, application_id=42)
    assert result["success"] is True
    assert result["status"] == "active"


@respx.mock
async def test_update_rejection_reason(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import update_rejection_reason

    lookup = respx.get(f"{HARVEST_BASE}/rejection_details").mock(
        return_value=httpx.Response(
            200, json=[{"id": 900, "application_id": 42, "rejection_reason_id": 1}]
        )
    )
    route = respx.patch(f"{HARVEST_BASE}/rejection_details/900").mock(
        return_value=httpx.Response(
            200, json={"id": 900, "application_id": 42, "rejection_reason_id": 5}
        )
    )
    result = await update_rejection_reason(client, application_id=42, rejection_reason_id=5)
    assert result["rejection_reason_id"] == 5
    assert lookup.calls[0].request.url.params["application_ids"] == "42"
    assert _body(route) == {"rejection_reason_id": 5}


@respx.mock
async def test_update_rejection_reason_not_rejected(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import update_rejection_reason

    respx.get(f"{HARVEST_BASE}/rejection_details").mock(return_value=httpx.Response(200, json=[]))
    result = await update_rejection_reason(client, application_id=42, rejection_reason_id=5)
    assert result["status_code"] == 404


@respx.mock
async def test_hire_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import hire_application

    route = respx.post(f"{HARVEST_BASE}/applications/42/hire").mock(
        return_value=httpx.Response(204)
    )
    result = await hire_application(
        client, application_id=42, start_date="2026-11-01", opening_id=3
    )
    assert result["status"] == "hired"
    assert _body(route) == {"start_date": "2026-11-01T00:00:00Z", "opening_id": 3}


@respx.mock
async def test_convert_prospect(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import convert_prospect

    route = respx.post(f"{HARVEST_BASE}/applications/42/convert_to_candidate").mock(
        return_value=httpx.Response(200, json=_app(id=42, prospect=False))
    )
    result = await convert_prospect(client, application_id=42, job_id=100, initial_stage_id=7)
    assert result["id"] == 42
    assert _body(route) == {"job_id": 100, "to_job_interview_stage_id": 7}


@respx.mock
async def test_add_attachment_to_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import add_attachment_to_application

    route = respx.post(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(201, json={"id": 77, "application_id": 42})
    )
    result = await add_attachment_to_application(
        client, application_id=42, filename="notes.pdf", type="admin_only", url="https://x/y.pdf"
    )
    assert result["id"] == 77
    assert _body(route) == {
        "application_id": 42,
        "filename": "notes.pdf",
        "type": "other",
        "url": "https://x/y.pdf",
        "visibility": "admin_only",
    }


async def test_add_attachment_to_application_validation(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.applications import add_attachment_to_application

    both = await add_attachment_to_application(
        client, application_id=1, filename="a.pdf", type="resume", content="QQ==", url="https://x"
    )
    assert both["status_code"] == 400
    bad_type = await add_attachment_to_application(
        client, application_id=1, filename="a.pdf", type="photo", content="QQ=="
    )
    assert bad_type["status_code"] == 400
    assert "resume" in bad_type["valid_types"]


def test_move_tools_are_detected_as_writes() -> None:
    """The server classifies tools as writes by scanning their source for harvest_post etc."""
    from greenhouse_mcp.harvest import applications

    for name in (
        "advance_application",
        "move_application",
        "move_application_same_job",
        "reject_application",
        "update_rejection_reason",
        "add_attachment_to_application",
    ):
        assert _is_write_tool(getattr(applications, name)), name
    for name in ("list_applications", "get_application"):
        assert not _is_write_tool(getattr(applications, name)), name

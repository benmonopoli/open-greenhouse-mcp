"""Harvest v3 tests for org-structure, permissions, custom fields, approvals, hiring team,
reference data and demographics tools."""
from __future__ import annotations

import json

import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


def _body(route: respx.Route, n: int = -1) -> dict:
    return json.loads(route.calls[n].request.content)


# ---------------------------------------------------------------------------
# User permissions
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_job_permissions(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.user_permissions import list_job_permissions

    perms = respx.get(f"{HARVEST_BASE}/user_job_permissions").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "job_id": 100, "user_id": 5, "role_id": 3, "automated": False}]
        )
    )
    respx.get(f"{HARVEST_BASE}/user_roles").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "Recruiter",
                                               "role_type": "job_admin"}])
    )
    result = await list_job_permissions(client, user_id=5)
    assert perms.calls.last.request.url.params["user_ids"] == "5"
    assert result["items"][0]["role_name"] == "Recruiter"


@respx.mock
async def test_add_job_permission(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.user_permissions import add_job_permission

    route = respx.post(f"{HARVEST_BASE}/user_job_permissions").mock(
        return_value=httpx.Response(201, json={"id": 1, "job_id": 100, "role_id": 3})
    )
    await add_job_permission(client, user_id=5, job_id=100, user_role_id=3)
    assert _body(route) == {"user_id": 5, "job_id": 100, "role_id": 3}


@respx.mock
async def test_remove_job_permission(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.user_permissions import remove_job_permission

    route = respx.delete(f"{HARVEST_BASE}/user_job_permissions/77").mock(
        return_value=httpx.Response(200, json={"id": 77, "message": "deleted"})
    )
    result = await remove_job_permission(client, user_id=5, job_permission_id=77)
    assert route.called
    assert result["id"] == 77


@respx.mock
async def test_future_job_permissions(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.user_permissions import (
        add_future_job_permission,
        list_future_job_permissions,
        remove_future_job_permission,
    )

    listing = respx.get(f"{HARVEST_BASE}/future_job_permissions").mock(
        return_value=httpx.Response(200, json=[{"id": 9, "user_id": 5, "role_id": 3,
                                               "office_id": None, "department_id": 2}])
    )
    respx.get(f"{HARVEST_BASE}/user_roles").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "Recruiter"}])
    )
    create = respx.post(f"{HARVEST_BASE}/future_job_permissions").mock(
        return_value=httpx.Response(201, json={"id": 10})
    )
    delete = respx.delete(f"{HARVEST_BASE}/future_job_permissions/9").mock(
        return_value=httpx.Response(200, json={"id": 9, "message": "deleted"})
    )
    result = await list_future_job_permissions(client, user_id=5)
    assert listing.calls.last.request.url.params["user_ids"] == "5"
    assert result["items"][0]["role_name"] == "Recruiter"
    await add_future_job_permission(client, user_id=5, user_role_id=3, department_id=2)
    assert _body(create) == {"user_id": 5, "role_id": 3, "department_id": 2}
    await remove_future_job_permission(client, user_id=5, future_job_permission_id=9)
    assert delete.called


@respx.mock
async def test_list_user_roles(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.user_roles import list_user_roles

    route = respx.get(f"{HARVEST_BASE}/user_roles").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "Recruiter",
                                               "role_type": "job_admin"}])
    )
    result = await list_user_roles(client)
    assert result["items"][0]["role_type"] == "job_admin"
    assert "page" not in route.calls.last.request.url.params


# ---------------------------------------------------------------------------
# Departments / offices writes
# ---------------------------------------------------------------------------

@respx.mock
async def test_create_department(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import create_department

    route = respx.post(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(201, json={"id": 8, "name": "Data"})
    )
    await create_department(client, name="Data", parent_id=1)
    assert _body(route) == {"name": "Data", "parent_id": 1}


@respx.mock
async def test_list_departments_parent_filter(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import list_departments

    route = respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "parent_id": 1}])
    )
    await list_departments(client, parent_id=1)
    assert route.calls.last.request.url.params["parent_id"] == "1"


@respx.mock
async def test_list_and_get_office(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offices import get_office, list_offices

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("ids") == "3":
            return httpx.Response(200, json=[{"id": 3, "name": "London", "location": "UK"}])
        if request.url.params.get("parent_id") == "3":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{"id": 3, "name": "London"}])

    respx.get(f"{HARVEST_BASE}/offices").mock(side_effect=handler)
    assert (await list_offices(client))["items"][0]["name"] == "London"
    office = await get_office(client, office_id=3)
    assert office["location"] == "UK"
    assert office["child_ids"] == []


@respx.mock
async def test_create_office(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offices import create_office

    route = respx.post(f"{HARVEST_BASE}/offices").mock(
        return_value=httpx.Response(201, json={"id": 4})
    )
    await create_office(client, name="Paris", location="Paris, FR", primary_contact_user_id=5)
    assert _body(route) == {"name": "Paris", "location": "Paris, FR",
                            "primary_in_house_contact_user_id": 5}


@respx.mock
async def test_update_office_with_name(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offices import update_office

    lookup = respx.get(f"{HARVEST_BASE}/offices")
    route = respx.patch(f"{HARVEST_BASE}/offices/4").mock(
        return_value=httpx.Response(200, json={"id": 4})
    )
    await update_office(client, office_id=4, name="Paris HQ", location="Paris")
    assert not lookup.called
    assert _body(route) == {"name": "Paris HQ", "location": "Paris"}


@respx.mock
async def test_update_office_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offices import update_office

    respx.get(f"{HARVEST_BASE}/offices").mock(return_value=httpx.Response(200, json=[]))
    result = await update_office(client, office_id=4, location="Paris")
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# Custom fields
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_custom_fields(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import list_custom_fields

    route = respx.get(f"{HARVEST_BASE}/custom_fields").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Cost Center",
                                               "field_type": "job"}])
    )
    result = await list_custom_fields(client, field_type="job")
    assert result["total"] == 1
    assert route.calls.last.request.url.params["field_type"] == "job"


@respx.mock
async def test_get_custom_field_with_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import get_custom_field

    respx.get(f"{HARVEST_BASE}/custom_fields").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "value_type": "single_select"}])
    )
    opts = respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
        return_value=httpx.Response(200, json=[
            {"id": 11, "name": "B", "sort_order": 2},
            {"id": 10, "name": "A", "sort_order": 1},
        ])
    )
    result = await get_custom_field(client, custom_field_id=1)
    assert opts.calls.last.request.url.params["custom_field_ids"] == "1"
    assert [o["name"] for o in result["custom_field_options"]] == ["A", "B"]


@respx.mock
async def test_get_custom_field_text_skips_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import get_custom_field

    respx.get(f"{HARVEST_BASE}/custom_fields").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "value_type": "short_text"}])
    )
    opts = respx.get(f"{HARVEST_BASE}/custom_field_options")
    result = await get_custom_field(client, custom_field_id=2)
    assert "custom_field_options" not in result
    assert not opts.called


@respx.mock
async def test_create_update_delete_custom_field(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import (
        create_custom_field,
        delete_custom_field,
        update_custom_field,
    )

    create = respx.post(f"{HARVEST_BASE}/custom_fields").mock(
        return_value=httpx.Response(201, json={"id": 5})
    )
    patch = respx.patch(f"{HARVEST_BASE}/custom_fields/5").mock(
        return_value=httpx.Response(200, json={"id": 5})
    )
    delete = respx.delete(f"{HARVEST_BASE}/custom_fields/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "message": "deleted"})
    )
    await create_custom_field(
        client, name="Level", field_type="job", value_type="single_select",
        options=[{"name": "L1", "priority": 3}, {"name": "L2"}],
    )
    body = _body(create)
    assert body["custom_field_options"] == [
        {"name": "L1", "sort_order": 3}, {"name": "L2", "sort_order": 1}
    ]
    await update_custom_field(client, custom_field_id=5, private=True)
    assert _body(patch) == {"private": True}
    await delete_custom_field(client, custom_field_id=5)
    assert delete.called


@respx.mock
async def test_list_custom_field_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import list_custom_field_options

    route = respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "sort_order": 5},
                                               {"id": 1, "sort_order": 0}])
    )
    result = await list_custom_field_options(client, custom_field_id=9, active=True)
    assert [o["id"] for o in result["items"]] == [1, 2]
    params = route.calls.last.request.url.params
    assert params["custom_field_ids"] == "9"
    assert params["active"] == "true"


@respx.mock
async def test_create_custom_field_options_individual(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import create_custom_field_options

    route = respx.post(f"{HARVEST_BASE}/custom_field_options").mock(
        side_effect=[httpx.Response(201, json={"id": 1}), httpx.Response(201, json={"id": 2})]
    )
    result = await create_custom_field_options(
        client, custom_field_id=9, options=[{"name": "A", "priority": 0}, {"name": "B"}]
    )
    assert result["count"] == 2
    assert _body(route, 0) == {"name": "A", "sort_order": 0, "custom_field_id": 9}
    assert _body(route, 1) == {"name": "B", "sort_order": 1, "custom_field_id": 9}


@respx.mock
async def test_create_custom_field_options_bulk(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import create_custom_field_options

    route = respx.post(f"{HARVEST_BASE}/custom_field_options/bulk").mock(
        return_value=httpx.Response(
            202, json={"bulk_action_uuid": "u-1", "status": "building", "status_url": "/x"}
        )
    )
    options = [{"name": f"Opt {i}"} for i in range(60)]
    result = await create_custom_field_options(client, custom_field_id=9, options=options)
    assert result["bulk_action_uuid"] == "u-1"
    assert "note" in result
    data = _body(route)["data"]
    assert len(data) == 60
    assert data[59] == {"name": "Opt 59", "sort_order": 59, "custom_field_id": 9}


@respx.mock
async def test_create_custom_field_options_partial_failure(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import create_custom_field_options

    respx.post(f"{HARVEST_BASE}/custom_field_options").mock(
        side_effect=[httpx.Response(201, json={"id": 1}),
                     httpx.Response(422, json={"message": "dup"})]
    )
    result = await create_custom_field_options(
        client, custom_field_id=9, options=[{"name": "A"}, {"name": "A"}]
    )
    assert result["count"] == 1
    assert result["errors"][0]["error"]["status_code"] == 422


@respx.mock
async def test_update_custom_field_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import update_custom_field_options

    route = respx.patch(f"{HARVEST_BASE}/custom_field_options/11").mock(
        return_value=httpx.Response(200, json={"id": 11, "name": "New"})
    )
    result = await update_custom_field_options(
        client, custom_field_id=9, options=[{"id": 11, "name": "New", "priority": 4}]
    )
    assert result["updated"][0]["name"] == "New"
    assert _body(route) == {"name": "New", "sort_order": 4}


async def test_update_custom_field_options_requires_ids(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import update_custom_field_options

    result = await update_custom_field_options(client, custom_field_id=9,
                                               options=[{"name": "x"}])
    assert result["status_code"] == 422


@respx.mock
async def test_update_custom_field_options_bulk(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import update_custom_field_options

    route = respx.patch(f"{HARVEST_BASE}/custom_field_options/bulk").mock(
        return_value=httpx.Response(202, json={"bulk_action_uuid": "u-2"})
    )
    options = [{"id": i, "name": f"N{i}"} for i in range(51)]
    result = await update_custom_field_options(client, custom_field_id=9, options=options)
    assert result["bulk_action_uuid"] == "u-2"
    assert _body(route)["data"][0] == {"name": "N0", "id": 0}


@respx.mock
async def test_delete_custom_field_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import delete_custom_field_options

    r1 = respx.delete(f"{HARVEST_BASE}/custom_field_options/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "message": "deleted"})
    )
    r2 = respx.delete(f"{HARVEST_BASE}/custom_field_options/2").mock(
        return_value=httpx.Response(404, json={})
    )
    result = await delete_custom_field_options(client, custom_field_id=9, option_ids=[1, 2])
    assert r1.called and r2.called
    assert result["deleted"] == [1]
    assert result["errors"][0]["option_id"] == 2


@respx.mock
async def test_delete_custom_field_options_all_fail(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import delete_custom_field_options

    respx.delete(f"{HARVEST_BASE}/custom_field_options/1").mock(
        return_value=httpx.Response(404, json={})
    )
    result = await delete_custom_field_options(client, custom_field_id=9, option_ids=[1])
    assert result["status_code"] == 404


@respx.mock
async def test_delete_custom_field_options_bulk(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.custom_fields import delete_custom_field_options

    route = respx.delete(f"{HARVEST_BASE}/custom_field_options/bulk").mock(
        return_value=httpx.Response(202, json={"bulk_action_uuid": "u-3"})
    )
    ids = list(range(1, 52))
    result = await delete_custom_field_options(client, custom_field_id=9, option_ids=ids)
    assert result["bulk_action_uuid"] == "u-3"
    assert _body(route) == {"data": ids}


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_rejection_reasons(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.rejection_reasons import list_rejection_reasons

    route = respx.get(f"{HARVEST_BASE}/rejection_reasons").mock(
        return_value=httpx.Response(200, json=[{
            "id": 1, "name": "Lacking skills",
            "type": {"id": 1, "key": "WE_REJECTED_THEM", "name": "We rejected them"},
        }])
    )
    result = await list_rejection_reasons(client, include_defaults=True)
    assert result["items"][0]["type"]["key"] == "WE_REJECTED_THEM"
    assert route.calls.last.request.url.params["include_defaults"] == "true"


@respx.mock
async def test_list_close_reasons(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.close_reasons import list_close_reasons

    respx.get(f"{HARVEST_BASE}/close_reasons").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Hired"}])
    )
    result = await list_close_reasons(client)
    assert result["items"][0]["name"] == "Hired"


@respx.mock
async def test_email_templates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.email_templates import get_email_template, list_email_templates

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("ids") == "4":
            return httpx.Response(200, json=[{"id": 4, "name": "Reject"}])
        assert request.url.params["email_type"] == "candidate_rejection"
        return httpx.Response(200, json=[{"id": 4, "name": "Reject"}])

    respx.get(f"{HARVEST_BASE}/email_templates").mock(side_effect=handler)
    listing = await list_email_templates(client, email_type="candidate_rejection")
    assert listing["items"][0]["id"] == 4
    assert (await get_email_template(client, email_template_id=4))["name"] == "Reject"


@respx.mock
async def test_get_tracking_link(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tracking_links import get_tracking_link

    route = respx.get(f"{HARVEST_BASE}/tracking_links").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "token": "abc", "source_id": 7}])
    )
    respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "LinkedIn"}])
    )
    result = await get_tracking_link(client, token="abc")
    assert route.calls.last.request.url.params["token"] == "abc"
    assert result["source"]["name"] == "LinkedIn"


@respx.mock
async def test_get_tracking_link_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tracking_links import get_tracking_link

    respx.get(f"{HARVEST_BASE}/tracking_links").mock(return_value=httpx.Response(200, json=[]))
    result = await get_tracking_link(client, token="nope")
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

@respx.mock
async def test_demographic_question_sets(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.demographics import (
        get_question_set,
        list_question_sets,
        list_questions_for_question_set,
    )

    sets = respx.get(f"{HARVEST_BASE}/demographic_question_sets").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "title": "US EEO"}])
    )
    questions = respx.get(f"{HARVEST_BASE}/demographic_questions").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "demographic_question_set_id": 1}])
    )
    assert (await list_question_sets(client))["items"][0]["title"] == "US EEO"
    assert (await get_question_set(client, question_set_id=1))["id"] == 1
    assert sets.calls.last.request.url.params["ids"] == "1"
    result = await list_questions_for_question_set(client, question_set_id=1)
    assert result["total"] == 1
    assert questions.calls.last.request.url.params["demographic_question_set_ids"] == "1"


@respx.mock
async def test_demographic_answer_options(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.demographics import (
        get_answer_option,
        get_question,
        list_answer_options,
        list_answer_options_for_question,
    )

    respx.get(f"{HARVEST_BASE}/demographic_questions").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Gender"}])
    )
    route = respx.get(f"{HARVEST_BASE}/demographic_answer_options").mock(
        return_value=httpx.Response(200, json=[{"id": 30, "demographic_question_id": 2}])
    )
    assert (await get_question(client, question_id=2))["name"] == "Gender"
    assert (await list_answer_options(client))["total"] == 1
    await list_answer_options_for_question(client, question_id=2)
    assert route.calls.last.request.url.params["demographic_question_ids"] == "2"
    assert (await get_answer_option(client, answer_option_id=30))["id"] == 30
    assert route.calls.last.request.url.params["ids"] == "30"


@respx.mock
async def test_demographic_answers(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.demographics import (
        get_answer,
        list_answers,
        list_answers_for_application,
    )

    route = respx.get(f"{HARVEST_BASE}/demographic_answers").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "application_id": 11}])
    )
    result = await list_answers(client, created_after="2026-01-01")
    assert result["items"][0]["id"] == 5
    assert route.calls.last.request.url.params["created_at[gt]"] == "2026-01-01T00:00:00Z"
    await list_answers_for_application(client, application_id=11)
    assert route.calls.last.request.url.params["application_ids"] == "11"
    assert (await get_answer(client, answer_id=5))["application_id"] == 11


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@respx.mock
async def test_get_approval_flow(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import get_approval_flow

    flows = respx.get(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "job_id": 100}])
    )
    groups = respx.get(f"{HARVEST_BASE}/approver_groups").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await get_approval_flow(client, job_id=100, approval_flow_id=1)
    assert flows.calls.last.request.url.params["ids"] == "1"
    assert groups.calls.last.request.url.params["approval_flow_ids"] == "1"
    assert result["approver_groups"] == []


@respx.mock
async def test_request_approvals(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import request_approvals

    route = respx.post(f"{HARVEST_BASE}/approval_flows/1/request_approvals").mock(
        return_value=httpx.Response(204)
    )
    assert await request_approvals(client, job_id=100, approval_flow_id=1) == {"success": True}
    assert route.called


@respx.mock
async def test_list_pending_approvals(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import list_pending_approvals

    approvers = respx.get(f"{HARVEST_BASE}/approvers").mock(
        return_value=httpx.Response(200, json=[
            {"id": 300, "approver_group_id": 20, "user_id": 5, "status": "due",
             "request_sent_at": "2026-01-01T00:00:00Z"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/approver_groups").mock(
        return_value=httpx.Response(200, json=[{"id": 20, "approval_flow_id": 1}])
    )
    respx.get(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "job_id": 100, "offer_id": None, "approval_type": "open_job",
             "approval_status": "pending"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "name": "Alice"}])
    )
    result = await list_pending_approvals(client, user_id=5)
    params = approvers.calls.last.request.url.params
    assert params["status"] == "due"
    assert params["user_ids"] == "5"
    assert approvers.call_count == 1
    item = result["items"][0]
    assert item["job_id"] == 100
    assert item["approval_type"] == "open_job"
    assert item["user_name"] == "Alice"


@respx.mock
async def test_list_pending_approvals_include_waiting(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import list_pending_approvals

    approvers = respx.get(f"{HARVEST_BASE}/approvers").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await list_pending_approvals(client, include_waiting=True)
    statuses = [c.request.url.params["status"] for c in approvers.calls]
    assert statuses == ["due", "waiting"]
    assert "user_ids" not in approvers.calls.last.request.url.params
    assert result == {"items": [], "total": 0}


@respx.mock
async def test_replace_approver(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import replace_approver

    respx.get(f"{HARVEST_BASE}/approver_groups").mock(
        return_value=httpx.Response(200, json=[{"id": 20, "approval_flow_id": 1},
                                               {"id": 21, "approval_flow_id": 1}])
    )
    approvers = respx.get(f"{HARVEST_BASE}/approvers").mock(
        return_value=httpx.Response(200, json=[
            {"id": 300, "approver_group_id": 21, "user_id": 5, "status": "waiting"},
        ])
    )
    put = respx.put(f"{HARVEST_BASE}/approver_groups/21/replace_approver").mock(
        return_value=httpx.Response(204)
    )
    result = await replace_approver(
        client, job_id=100, approval_flow_id=1, remove_user_id=5, add_user_id=6
    )
    assert result == {"success": True}
    params = approvers.calls.last.request.url.params
    assert params["approver_group_ids"] == "20,21"
    assert params["user_ids"] == "5"
    assert _body(put) == {"remove_user_id": 5, "add_user_id": 6}


@respx.mock
async def test_replace_approver_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import replace_approver

    respx.get(f"{HARVEST_BASE}/approver_groups").mock(
        return_value=httpx.Response(200, json=[{"id": 20}])
    )
    respx.get(f"{HARVEST_BASE}/approvers").mock(return_value=httpx.Response(200, json=[]))
    result = await replace_approver(
        client, job_id=100, approval_flow_id=1, remove_user_id=5, add_user_id=6
    )
    assert result["status_code"] == 404


@respx.mock
async def test_create_approval_flow_when_none_exists(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import create_or_replace_approval_flow

    lookup = respx.get(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(200, json=[])
    )
    create = respx.post(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    await create_or_replace_approval_flow(
        client, job_id=100, approval_type="open_job",
        approver_groups=[{"approvals_required": 1, "approvers": [{"id": 5}, {"email": "a@x"}]}],
    )
    params = lookup.calls.last.request.url.params
    assert params["job_ids"] == "100"
    assert params["approval_type"] == "open_job"
    assert _body(create) == {
        "job_id": 100, "approval_type": "open_job", "sequential": True,
        "approver_groups": [{"approvals_required": 1,
                             "approvers": [{"user_id": 5}, {"email": "a@x"}]}],
    }


@respx.mock
async def test_replace_existing_approval_flow(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import create_or_replace_approval_flow

    respx.get(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(200, json=[{"id": 9, "offer_id": None, "sequential": True}])
    )
    create = respx.post(f"{HARVEST_BASE}/approval_flows")
    patch = respx.patch(f"{HARVEST_BASE}/approval_flows/9").mock(
        return_value=httpx.Response(200, json={"id": 9, "sequential": False})
    )
    put = respx.put(f"{HARVEST_BASE}/approval_flows/9/replace_approver_groups").mock(
        return_value=httpx.Response(200, json={"id": 9})
    )
    result = await create_or_replace_approval_flow(
        client, job_id=100, approval_type="open_job", sequential=False,
        approver_groups=[{"approvals_required": 1, "approvers": [{"user_id": 5}]}],
    )
    assert result["id"] == 9
    assert not create.called
    assert _body(patch) == {"sequential": False}
    assert _body(put) == {"approver_groups": [{"approvals_required": 1,
                                               "approvers": [{"user_id": 5}]}]}


# ---------------------------------------------------------------------------
# Hiring team writes
# ---------------------------------------------------------------------------

def _mock_team() -> None:
    respx.get(f"{HARVEST_BASE}/job_hiring_managers").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "job_id": 100, "user_id": 7}])
    )
    respx.get(f"{HARVEST_BASE}/job_owners").mock(
        return_value=httpx.Response(200, json=[
            {"id": 2, "job_id": 100, "user_id": 5, "type": "recruiter", "responsible": True},
            {"id": 3, "job_id": 100, "user_id": 7, "type": "sourcer", "responsible": False},
        ])
    )


@respx.mock
async def test_replace_hiring_team(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import replace_hiring_team

    _mock_team()
    del_owner = respx.delete(f"{HARVEST_BASE}/job_owners/2").mock(
        return_value=httpx.Response(200, json={"id": 2, "message": "deleted"})
    )
    add_owner = respx.post(f"{HARVEST_BASE}/job_owners").mock(
        return_value=httpx.Response(201, json={"id": 4})
    )
    add_hm = respx.post(f"{HARVEST_BASE}/job_hiring_managers").mock(
        return_value=httpx.Response(201, json={"id": 5})
    )
    del_hm = respx.delete(f"{HARVEST_BASE}/job_hiring_managers/1")
    result = await replace_hiring_team(
        client, job_id=100,
        recruiters=[{"user_id": 6, "candidate_responsibility": "all"}],
        hiring_managers=[{"user_id": 7}, {"user_id": 8}],
    )
    assert del_owner.called
    assert not del_hm.called  # user 7 stays a hiring manager
    assert _body(add_owner) == {"job_id": 100, "user_id": 6, "type": "recruiter",
                                "candidate_responsibility": "all"}
    assert _body(add_hm) == {"job_id": 100, "user_id": 8}
    assert {"role": "recruiters", "user_id": 5} in result["removed"]
    assert len(result["added"]) == 2
    assert "errors" not in result


@respx.mock
async def test_add_hiring_team_members(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import add_hiring_team_members

    route = respx.post(f"{HARVEST_BASE}/job_owners").mock(
        return_value=httpx.Response(201, json={"id": 4})
    )
    result = await add_hiring_team_members(
        client, job_id=100, coordinators=[{"user_id": 9}], sourcers=[{"id": 10}]
    )
    assert _body(route, 0) == {"job_id": 100, "user_id": 9, "type": "coordinator"}
    assert _body(route, 1) == {"job_id": 100, "user_id": 10, "type": "sourcer"}
    assert len(result["added"]) == 2


@respx.mock
async def test_add_hiring_team_members_all_fail(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import add_hiring_team_members

    respx.post(f"{HARVEST_BASE}/job_hiring_managers").mock(
        return_value=httpx.Response(422, json={"message": "already assigned"})
    )
    result = await add_hiring_team_members(client, job_id=100, hiring_managers=[{"user_id": 7}])
    assert result["status_code"] == 422


@respx.mock
async def test_remove_hiring_team_member(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import remove_hiring_team_member

    _mock_team()
    del_hm = respx.delete(f"{HARVEST_BASE}/job_hiring_managers/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "message": "deleted"})
    )
    del_owner = respx.delete(f"{HARVEST_BASE}/job_owners/3").mock(
        return_value=httpx.Response(200, json={"id": 3, "message": "deleted"})
    )
    result = await remove_hiring_team_member(client, job_id=100, user_id=7)
    assert del_hm.called and del_owner.called
    assert len(result["removed"]) == 2


@respx.mock
async def test_remove_hiring_team_member_not_on_team(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import remove_hiring_team_member

    _mock_team()
    result = await remove_hiring_team_member(client, job_id=100, user_id=99)
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# Write-tool classification (server profiles inspect each tool's source)
# ---------------------------------------------------------------------------

def test_write_tools_are_detected() -> None:
    from greenhouse_mcp.harvest import (
        approvals,
        custom_fields,
        hiring_team,
        tags,
        user_permissions,
        users,
    )
    from greenhouse_mcp.server import _is_write_tool

    writes = [
        users.disable_user, users.enable_user, users.change_user_permission_level,
        users.add_email_to_user, user_permissions.add_job_permission,
        tags.add_tag_to_candidate, tags.remove_tag_from_candidate,
        custom_fields.create_custom_field_options, custom_fields.update_custom_field_options,
        custom_fields.delete_custom_field_options, approvals.replace_approver,
        approvals.create_or_replace_approval_flow, approvals.request_approvals,
        hiring_team.replace_hiring_team, hiring_team.add_hiring_team_members,
        hiring_team.remove_hiring_team_member,
    ]
    reads = [
        users.get_user, users.list_users, user_permissions.list_job_permissions,
        tags.list_tags_on_candidate, approvals.list_pending_approvals,
        approvals.list_approvals_for_job, hiring_team.get_hiring_team,
        custom_fields.get_custom_field,
    ]
    assert all(_is_write_tool(fn) for fn in writes)
    assert not any(_is_write_tool(fn) for fn in reads)

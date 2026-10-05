"""Tests for remaining harvest modules: users, depts, tags, demographics, etc. (Harvest v3)."""
from __future__ import annotations

import json

import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


def _body(route: respx.Route) -> dict:
    return json.loads(route.calls.last.request.content)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_users(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import list_users

    route = respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Alice", "deactivated": False}])
    )
    result = await list_users(client, created_after="2025-01-01T00:00:00Z")
    assert result["items"][0]["name"] == "Alice"
    assert result["has_next"] is False
    params = route.calls.last.request.url.params
    assert params["created_at[gt]"] == "2025-01-01T00:00:00Z"
    assert params["per_page"] == "500"
    assert "page" not in params


@respx.mock
async def test_list_users_cursor_drops_other_params(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import list_users

    route = respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 2}],
            headers={"link": f'<{HARVEST_BASE}/users?cursor=next123>; rel="next"'},
        )
    )
    result = await list_users(client, cursor="abc", deactivated=True)
    assert dict(route.calls.last.request.url.params) == {"cursor": "abc"}
    assert result["next_cursor"] == "next123"


@respx.mock
async def test_list_users_by_primary_email(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import list_users

    route = respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "primary_email": "a@x.com"}])
    )
    result = await list_users(client, email="a@x.com")
    assert result["items"][0]["id"] == 3
    assert route.calls.last.request.url.params["primary_email"] == "a@x.com"


@respx.mock
async def test_list_users_by_secondary_email(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import list_users

    users = respx.get(f"{HARVEST_BASE}/users").mock(
        side_effect=[httpx.Response(200, json=[]), httpx.Response(200, json=[{"id": 9}])]
    )
    emails = respx.get(f"{HARVEST_BASE}/user_emails").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "user_id": 9, "email": "b@x.com"}])
    )
    result = await list_users(client, email="b@x.com")
    assert result["items"] == [{"id": 9}]
    assert emails.calls.last.request.url.params["email"] == "b@x.com"
    second = users.calls[1].request.url.params
    assert second["ids"] == "9"
    assert "primary_email" not in second


@respx.mock
async def test_get_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import get_user

    users = respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(
            200, json=[{"id": 10, "name": "Bob", "department_ids": [4], "office_ids": []}]
        )
    )
    depts = respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(200, json=[{"id": 4, "name": "Engineering"}])
    )
    respx.get(f"{HARVEST_BASE}/user_emails").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "user_id": 10, "email": "bob@x.com", "verified": True}]
        )
    )
    result = await get_user(client, user_id=10)
    assert result["id"] == 10
    assert users.calls.last.request.url.params["ids"] == "10"
    assert depts.calls.last.request.url.params["ids"] == "4"
    assert result["departments"] == [{"id": 4, "name": "Engineering"}]
    assert result["offices"] == []
    assert result["emails"] == [{"email": "bob@x.com", "verified": True}]


@respx.mock
async def test_get_user_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import get_user

    respx.get(f"{HARVEST_BASE}/users").mock(return_value=httpx.Response(200, json=[]))
    result = await get_user(client, user_id=404)
    assert result["status_code"] == 404


@respx.mock
async def test_create_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import create_user

    route = respx.post(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(201, json={"id": 99, "first_name": "Carol"})
    )
    result = await create_user(
        client, first_name="Carol", last_name="Smith", email="carol@example.com"
    )
    assert result["id"] == 99
    body = _body(route)
    assert body["primary_email"] == "carol@example.com"
    assert body["send_email_invite"] is True
    assert "email" not in body


@respx.mock
async def test_update_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import update_user

    route = respx.patch(f"{HARVEST_BASE}/users/10").mock(
        return_value=httpx.Response(200, json={"id": 10, "first_name": "Rob"})
    )
    await update_user(client, user_id=10, first_name="Rob", job_title="Recruiter")
    assert _body(route) == {"first_name": "Rob", "job_title": "Recruiter"}


@respx.mock
async def test_disable_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import disable_user

    route = respx.post(f"{HARVEST_BASE}/users/10/deactivate").mock(
        return_value=httpx.Response(204)
    )
    result = await disable_user(client, user_id=10)
    assert result == {"success": True}
    assert route.called


@respx.mock
async def test_enable_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import enable_user

    route = respx.post(f"{HARVEST_BASE}/users/10/activate").mock(
        return_value=httpx.Response(204)
    )
    assert await enable_user(client, user_id=10) == {"success": True}
    assert route.called


@respx.mock
async def test_change_user_permission_level_basic(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import change_user_permission_level

    route = respx.post(f"{HARVEST_BASE}/users/10/revoke_permissions").mock(
        return_value=httpx.Response(204)
    )
    assert await change_user_permission_level(client, user_id=10) == {"success": True}
    assert route.called


async def test_change_user_permission_level_rejects_promotion(
    client: GreenhouseClient,
) -> None:
    from greenhouse_mcp.harvest.users import change_user_permission_level

    result = await change_user_permission_level(
        client, user_id=10, permission_level="site_admin"
    )
    assert result["status_code"] == 422


@respx.mock
async def test_add_email_to_user(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.users import add_email_to_user

    route = respx.post(f"{HARVEST_BASE}/user_emails").mock(
        return_value=httpx.Response(201, json={"id": 5, "user_id": 10, "verified": False})
    )
    result = await add_email_to_user(client, user_id=10, email="new@x.com")
    assert result["id"] == 5
    assert _body(route) == {"user_id": 10, "email": "new@x.com", "send_verification": True}


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_departments(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import list_departments

    respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Engineering"}])
    )
    result = await list_departments(client)
    assert result["items"][0]["name"] == "Engineering"


@respx.mock
async def test_get_department(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import get_department

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("ids") == "5":
            return httpx.Response(200, json=[{"id": 5, "name": "Design", "parent_id": None}])
        assert request.url.params["parent_id"] == "5"
        return httpx.Response(200, json=[{"id": 6, "name": "UX", "parent_id": 5}])

    respx.get(f"{HARVEST_BASE}/departments").mock(side_effect=handler)
    result = await get_department(client, department_id=5)
    assert result["name"] == "Design"
    assert result["child_ids"] == [6]


@respx.mock
async def test_update_department_keeps_name(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.departments import update_department

    respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "name": "Design"}])
    )
    route = respx.patch(f"{HARVEST_BASE}/departments/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Design", "parent_id": 1})
    )
    await update_department(client, department_id=5, parent_id=1)
    assert _body(route) == {"name": "Design", "parent_id": 1}


# ---------------------------------------------------------------------------
# Sources (cached)
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_sources(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.sources import list_sources

    respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "name": "LinkedIn", "type": {"id": 2, "name": "Prospecting"}}]
        )
    )
    result = await list_sources(client)
    assert result["items"][0]["name"] == "LinkedIn"


@respx.mock
async def test_list_sources_cached(client: GreenhouseClient) -> None:
    """Second call with same client should use cache and not hit network."""
    from greenhouse_mcp.harvest.sources import list_sources

    route = respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Referral"}])
    )
    result1 = await list_sources(client)
    result2 = await list_sources(client)
    assert result1 == result2
    assert route.call_count == 1


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_tags(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import list_tags

    respx.get(f"{HARVEST_BASE}/candidate_tags").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "priority"}])
    )
    result = await list_tags(client)
    assert result["items"][0]["name"] == "priority"


@respx.mock
async def test_create_and_delete_tag(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import create_tag, delete_tag

    create = respx.post(f"{HARVEST_BASE}/candidate_tags").mock(
        return_value=httpx.Response(201, json={"id": 8, "name": "hot"})
    )
    delete = respx.delete(f"{HARVEST_BASE}/candidate_tags/8").mock(
        return_value=httpx.Response(200, json={"id": 8, "message": "deleted"})
    )
    assert (await create_tag(client, name="hot"))["id"] == 8
    assert _body(create) == {"name": "hot"}
    assert (await delete_tag(client, tag_id=8))["id"] == 8
    assert delete.called


@respx.mock
async def test_list_tags_on_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import list_tags_on_candidate

    applied = respx.get(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 70, "candidate_id": 42, "candidate_tag_id": 7,
                   "created_at": "2026-01-01T00:00:00Z"}],
        )
    )
    tags = respx.get(f"{HARVEST_BASE}/candidate_tags").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "referred"}])
    )
    result = await list_tags_on_candidate(client, candidate_id=42)
    assert applied.calls.last.request.url.params["candidate_ids"] == "42"
    assert tags.calls.last.request.url.params["ids"] == "7"
    assert result["items"] == [{"id": 7, "name": "referred", "applied_tag_id": 70,
                                "applied_at": "2026-01-01T00:00:00Z"}]


@respx.mock
async def test_add_tag_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import add_tag_to_candidate

    route = respx.post(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(
            201, json={"id": 70, "candidate_id": 42, "candidate_tag_id": 7}
        )
    )
    result = await add_tag_to_candidate(client, candidate_id=42, tag_id=7)
    assert result["candidate_tag_id"] == 7
    assert _body(route) == {"candidate_id": 42, "candidate_tag_id": 7}


@respx.mock
async def test_remove_tag_from_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import remove_tag_from_candidate

    lookup = respx.get(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(
            200, json=[{"id": 70, "candidate_id": 42, "candidate_tag_id": 7}]
        )
    )
    delete = respx.delete(f"{HARVEST_BASE}/applied_candidate_tags/70").mock(
        return_value=httpx.Response(200, json={"id": 70, "message": "deleted"})
    )
    result = await remove_tag_from_candidate(client, candidate_id=42, tag_id=7)
    params = lookup.calls.last.request.url.params
    assert params["candidate_ids"] == "42"
    assert params["candidate_tag_ids"] == "7"
    assert delete.called
    assert result["id"] == 70


@respx.mock
async def test_remove_tag_not_applied(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.tags import remove_tag_from_candidate

    respx.get(f"{HARVEST_BASE}/applied_candidate_tags").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await remove_tag_from_candidate(client, candidate_id=42, tag_id=7)
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# Activity Feed
# ---------------------------------------------------------------------------

@respx.mock
async def test_get_activity_feed(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.activity_feed import get_activity_feed

    notes = respx.get(f"{HARVEST_BASE}/notes").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "type": "NOTE", "body": "Great call", "user_id": 5,
             "created_at": "2026-01-01T00:00:00Z"},
            {"id": 2, "type": "EMAIL", "subject": "Hi", "user_id": 5,
             "created_at": "2026-01-03T00:00:00Z"},
            {"id": 3, "type": "ACTIVITY", "body": "Moved to Onsite", "user_id": None,
             "created_at": "2026-01-02T00:00:00Z"},
            {"id": 4, "type": "INTERVIEW", "body": "Panel", "user_id": None,
             "created_at": "2026-01-04T00:00:00Z"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "name": "Alice"}])
    )
    result = await get_activity_feed(client, candidate_id=42)
    assert notes.calls.last.request.url.params["candidate_ids"] == "42"
    assert [n["id"] for n in result["notes"]] == [4, 1]  # newest first
    assert result["emails"][0]["user"] == {"id": 5, "name": "Alice"}
    assert result["activities"][0]["user"] is None
    assert result["total"] == 4


# ---------------------------------------------------------------------------
# EEOC
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_eeoc(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.eeoc import list_eeoc

    route = respx.get(f"{HARVEST_BASE}/eeoc").mock(
        return_value=httpx.Response(200, json=[{"application_id": 1, "candidate_id": 2}])
    )
    result = await list_eeoc(client, submitted_after="2026-01-01")
    assert result["items"][0]["application_id"] == 1
    assert route.calls.last.request.url.params["submitted_at[gt]"] == "2026-01-01T00:00:00Z"


@respx.mock
async def test_get_eeoc_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.eeoc import get_eeoc_for_application

    route = respx.get(f"{HARVEST_BASE}/eeoc").mock(
        return_value=httpx.Response(200, json=[{"application_id": 11, "gender": {"id": 1}}])
    )
    result = await get_eeoc_for_application(client, application_id=11)
    assert result["application_id"] == 11
    assert route.calls.last.request.url.params["application_ids"] == "11"


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_questions(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.demographics import list_questions

    respx.get(f"{HARVEST_BASE}/demographic_questions").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Gender"}])
    )
    result = await list_questions(client)
    assert result["items"][0]["name"] == "Gender"


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_approvals_for_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.approvals import list_approvals_for_job

    flows = respx.get(f"{HARVEST_BASE}/approval_flows").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "job_id": 100, "approval_status": "pending"}]
        )
    )
    respx.get(f"{HARVEST_BASE}/approver_groups").mock(
        return_value=httpx.Response(200, json=[
            {"id": 21, "approval_flow_id": 1, "sort_order": 1, "approvals_required": 1},
            {"id": 20, "approval_flow_id": 1, "sort_order": 0, "approvals_required": 1},
        ])
    )
    respx.get(f"{HARVEST_BASE}/approvers").mock(
        return_value=httpx.Response(200, json=[
            {"id": 300, "approver_group_id": 20, "user_id": 5, "status": "due"},
        ])
    )
    respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "name": "Alice"}])
    )
    result = await list_approvals_for_job(client, job_id=100)
    assert flows.calls.last.request.url.params["job_ids"] == "100"
    flow = result["items"][0]
    assert flow["approval_status"] == "pending"
    assert [g["id"] for g in flow["approver_groups"]] == [20, 21]
    assert flow["approver_groups"][0]["approvers"][0]["user_name"] == "Alice"
    assert flow["approver_groups"][1]["approvers"] == []


# ---------------------------------------------------------------------------
# Hiring Team
# ---------------------------------------------------------------------------

@respx.mock
async def test_get_hiring_team(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.hiring_team import get_hiring_team

    hms = respx.get(f"{HARVEST_BASE}/job_hiring_managers").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "job_id": 100, "user_id": 7}])
    )
    respx.get(f"{HARVEST_BASE}/job_owners").mock(
        return_value=httpx.Response(200, json=[
            {"id": 2, "job_id": 100, "user_id": 5, "type": "recruiter", "responsible": True},
            {"id": 3, "job_id": 100, "user_id": 6, "type": "sourcer", "responsible": False},
        ])
    )
    respx.get(f"{HARVEST_BASE}/users").mock(
        return_value=httpx.Response(200, json=[
            {"id": 5, "name": "Rita", "first_name": "Rita", "last_name": "R"},
            {"id": 6, "name": "Sam"},
            {"id": 7, "name": "Hank"},
        ])
    )
    result = await get_hiring_team(client, job_id=100)
    assert hms.calls.last.request.url.params["job_ids"] == "100"
    assert result["recruiters"][0]["id"] == 5
    assert result["recruiters"][0]["responsible"] is True
    assert result["recruiters"][0]["assignment_id"] == 2
    assert result["hiring_managers"][0]["name"] == "Hank"
    assert result["sourcers"][0]["name"] == "Sam"
    assert result["coordinators"] == []


# ---------------------------------------------------------------------------
# Prospect Pools
# ---------------------------------------------------------------------------

@respx.mock
async def test_list_prospect_pools(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.prospect_pools import list_prospect_pools

    respx.get(f"{HARVEST_BASE}/prospect_pools").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Executive Pool"}])
    )
    stages = respx.get(f"{HARVEST_BASE}/prospect_pool_stages").mock(
        return_value=httpx.Response(200, json=[
            {"id": 11, "prospect_pool_id": 1, "name": "Contacted", "sort_order": 2},
            {"id": 10, "prospect_pool_id": 1, "name": "New", "sort_order": 1},
        ])
    )
    result = await list_prospect_pools(client)
    assert result["items"][0]["name"] == "Executive Pool"
    assert stages.calls.last.request.url.params["prospect_pool_ids"] == "1"
    assert [s["name"] for s in result["items"][0]["prospect_stages"]] == ["New", "Contacted"]


@respx.mock
async def test_get_prospect_pool(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.prospect_pools import get_prospect_pool

    route = respx.get(f"{HARVEST_BASE}/prospect_pools").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Executive Pool"}])
    )
    respx.get(f"{HARVEST_BASE}/prospect_pool_stages").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await get_prospect_pool(client, prospect_pool_id=1)
    assert result["id"] == 1
    assert result["prospect_stages"] == []
    assert route.calls.last.request.url.params["ids"] == "1"

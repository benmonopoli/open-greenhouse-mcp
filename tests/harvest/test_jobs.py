"""Tests for harvest/jobs.py, job_posts.py, job_stages.py, job_openings.py (Harvest v3)."""
from __future__ import annotations

import json

import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v3"


def _ok(payload: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def _params(route: respx.Route) -> dict[str, str]:
    return dict(route.calls.last.request.url.params)


def _body(route: respx.Route) -> dict:
    return json.loads(route.calls.last.request.content)


# --- jobs ---

@respx.mock
async def test_list_jobs_hydrates_department_and_offices(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import list_jobs

    jobs = respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=_ok([
        {"id": 1, "name": "Engineer", "status": "open", "department_id": 10,
         "office_ids": [20, 21]},
    ]))
    depts = respx.get(f"{HARVEST_BASE}/departments").mock(
        return_value=_ok([{"id": 10, "name": "Engineering"}])
    )
    offices = respx.get(f"{HARVEST_BASE}/offices").mock(
        return_value=_ok([{"id": 20, "name": "London"}, {"id": 21, "name": "Remote"}])
    )
    result = await list_jobs(
        client, status="open", department_id=10, created_after="2026-01-01T00:00:00Z"
    )
    params = _params(jobs)
    assert params["status"] == "open"
    assert params["department_id"] == "10"
    assert params["created_at[gte]"] == "2026-01-01T00:00:00Z"
    assert "page" not in params
    assert _params(depts)["ids"] == "10"
    assert _params(offices)["ids"] == "20,21"
    job = result["items"][0]
    assert job["department"] == {"id": 10, "name": "Engineering"}
    assert job["offices"] == [{"id": 20, "name": "London"}, {"id": 21, "name": "Remote"}]
    assert result["has_next"] is False
    assert "warnings" not in result


@respx.mock
async def test_list_jobs_cursor_and_next_page(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import list_jobs

    route = respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(
        200, json=[{"id": 2, "department_id": None, "office_ids": []}],
        headers={"link": f'<{HARVEST_BASE}/jobs?cursor=next123>; rel="next"'},
    ))
    result = await list_jobs(client, cursor="abc", status="open")
    assert _params(route) == {"cursor": "abc"}
    assert result["next_cursor"] == "next123"
    assert result["items"][0]["department"] is None


@respx.mock
async def test_list_jobs_lookup_failure_adds_warning(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import list_jobs

    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=_ok([{"id": 1, "department_id": 10, "office_ids": []}])
    )
    respx.get(f"{HARVEST_BASE}/departments").mock(return_value=_ok({}, 403))
    result = await list_jobs(client)
    assert result["items"][0]["department"] == {"id": 10, "name": None}
    assert "departments" in result["warnings"][0]


@respx.mock
async def test_get_job_embeds_openings_and_hiring_team(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import get_job

    jobs = respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=_ok([
        {"id": 42, "name": "Designer", "department_id": None, "office_ids": [20]},
    ]))
    respx.get(f"{HARVEST_BASE}/offices").mock(return_value=_ok([{"id": 20, "name": "NYC"}]))
    openings = respx.get(f"{HARVEST_BASE}/openings").mock(return_value=_ok([
        {"id": 2, "job_id": 42, "open": True, "sort_order": 2},
        {"id": 1, "job_id": 42, "open": False, "sort_order": 1},
    ]))
    respx.get(f"{HARVEST_BASE}/job_hiring_managers").mock(
        return_value=_ok([{"id": 5, "job_id": 42, "user_id": 100}])
    )
    respx.get(f"{HARVEST_BASE}/job_owners").mock(return_value=_ok([
        {"id": 6, "job_id": 42, "user_id": 101, "type": "recruiter", "responsible": True},
        {"id": 7, "job_id": 42, "user_id": 102, "type": "coordinator", "responsible": False},
    ]))
    users = respx.get(f"{HARVEST_BASE}/users").mock(return_value=_ok([
        {"id": 100, "name": "Hana Manager", "primary_email": "h@x.com"},
        {"id": 101, "first_name": "Rita", "last_name": "Recruiter", "primary_email": "r@x.com"},
        {"id": 102, "name": None, "primary_email": "c@x.com"},
    ]))
    result = await get_job(client, job_id=42)
    assert _params(jobs)["ids"] == "42"
    assert _params(openings)["job_ids"] == "42"
    assert _params(users)["ids"] == "100,101,102"
    assert result["id"] == 42
    assert [o["id"] for o in result["openings"]] == [1, 2]
    team = result["hiring_team"]
    assert team["hiring_managers"] == [{"id": 100, "name": "Hana Manager", "email": "h@x.com"}]
    assert team["recruiters"][0]["name"] == "Rita Recruiter"
    assert team["recruiters"][0]["responsible"] is True
    assert team["coordinators"][0]["name"] == "c@x.com"
    assert team["sourcers"] == []
    assert result["offices"] == [{"id": 20, "name": "NYC"}]


@respx.mock
async def test_get_job_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import get_job

    respx.get(f"{HARVEST_BASE}/jobs").mock(return_value=_ok([]))
    result = await get_job(client, job_id=999)
    assert result["status_code"] == 404


@respx.mock
async def test_create_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import create_job

    route = respx.post(f"{HARVEST_BASE}/jobs").mock(
        return_value=_ok({"id": 99, "name": "PM"}, 201)
    )
    result = await create_job(
        client, template_job_id=5, job_name="PM", office_ids=[1],
        custom_fields=[{"id": 7, "value": "x"}, {"name_key": "level", "value": "L3"}],
    )
    assert result["id"] == 99
    body = _body(route)
    assert body["template_job_id"] == 5
    assert body["number_of_openings"] == 1
    assert body["job_name"] == "PM"
    assert body["office_ids"] == [1]
    assert body["custom_fields"] == [
        {"custom_field_id": 7, "value": "x"}, {"name_key": "level", "value": "L3"},
    ]
    assert "department_id" not in body


@respx.mock
async def test_update_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import update_job

    route = respx.patch(f"{HARVEST_BASE}/jobs/42").mock(
        return_value=_ok({"id": 42, "name": "Lead Designer"})
    )
    result = await update_job(client, job_id=42, name="Lead Designer", notes="<p>hi</p>")
    assert result["name"] == "Lead Designer"
    assert _body(route) == {"name": "Lead Designer", "notes": "<p>hi</p>"}


@respx.mock
async def test_update_job_status_is_rejected_without_call(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.jobs import update_job

    route = respx.patch(f"{HARVEST_BASE}/jobs/42").mock(return_value=_ok({}))
    result = await update_job(client, job_id=42, status="closed")
    assert result["status_code"] == 422
    assert "update_job_opening" in result["error"]
    assert not route.called


# --- job_posts ---

def _mock_post_locations() -> respx.Route:
    respx.get(f"{HARVEST_BASE}/offices").mock(return_value=_ok([{"id": 20, "name": "London"}]))
    respx.get(f"{HARVEST_BASE}/job_board_custom_locations").mock(
        return_value=_ok([{"id": 30, "value": "Remote (EU)", "active": True}])
    )
    return respx.get(f"{HARVEST_BASE}/job_post_locations").mock(return_value=_ok([
        {"id": 1, "job_post_id": 10, "type": "free_text", "plain_text_location": "NYC"},
        {"id": 2, "job_post_id": 10, "type": "office", "office_id": 20},
        {"id": 3, "job_post_id": 10, "type": "custom_list", "custom_location_id": 30},
    ]))


@respx.mock
async def test_list_job_posts_attaches_locations(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import list_job_posts

    posts = respx.get(f"{HARVEST_BASE}/job_posts").mock(return_value=_ok([
        {"id": 10, "title": "Senior Dev", "job_id": 42, "questions": [{"label": "Resume"}]},
        {"id": 11, "title": "Other", "job_id": 43, "questions": []},
    ]))
    locs = _mock_post_locations()
    result = await list_job_posts(client, live=True)
    assert _params(posts)["live"] == "true"
    assert _params(locs)["job_post_ids"] == "10,11"
    post = result["items"][0]
    assert [loc["name"] for loc in post["locations"]] == ["NYC", "London", "Remote (EU)"]
    assert post["questions"] == [{"label": "Resume"}]
    assert result["items"][1]["locations"] == []


@respx.mock
async def test_list_job_posts_for_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import list_job_posts_for_job

    posts = respx.get(f"{HARVEST_BASE}/job_posts").mock(
        return_value=_ok([{"id": 11, "job_id": 42}])
    )
    respx.get(f"{HARVEST_BASE}/job_post_locations").mock(return_value=_ok([]))
    result = await list_job_posts_for_job(client, job_id=42)
    assert _params(posts)["job_ids"] == "42"
    assert result["items"] == [{"id": 11, "job_id": 42, "locations": []}]
    assert result["total"] == 1


@respx.mock
async def test_get_job_post(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import get_job_post

    posts = respx.get(f"{HARVEST_BASE}/job_posts").mock(
        return_value=_ok([{"id": 10, "title": "Dev", "job_id": 42}])
    )
    _mock_post_locations()
    result = await get_job_post(client, job_post_id=10)
    assert _params(posts)["ids"] == "10"
    assert result["id"] == 10
    assert len(result["locations"]) == 3


@respx.mock
async def test_get_job_post_for_job_checks_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import get_job_post_for_job

    respx.get(f"{HARVEST_BASE}/job_posts").mock(return_value=_ok([{"id": 10, "job_id": 42}]))
    respx.get(f"{HARVEST_BASE}/job_post_locations").mock(return_value=_ok([]))
    ok = await get_job_post_for_job(client, job_id=42, job_post_id=10)
    assert ok["id"] == 10
    wrong = await get_job_post_for_job(client, job_id=7, job_post_id=10)
    assert wrong["status_code"] == 404


@respx.mock
async def test_get_job_post_custom_locations(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import get_job_post_custom_locations

    locs = respx.get(f"{HARVEST_BASE}/job_post_locations").mock(return_value=_ok([
        {"id": 3, "job_post_id": 10, "type": "custom_list", "custom_location_id": 30},
    ]))
    customs = respx.get(f"{HARVEST_BASE}/job_board_custom_locations").mock(
        return_value=_ok([{"id": 30, "value": "Remote (EU)", "greenhouse_job_board_id": 1}])
    )
    result = await get_job_post_custom_locations(client, job_post_id=10)
    assert _params(locs)["type"] == "custom_list"
    assert _params(customs)["ids"] == "30"
    assert result["items"] == [{
        "id": 30, "value": "Remote (EU)", "greenhouse_job_board_id": 1,
        "job_post_location_id": 3,
    }]


@respx.mock
async def test_update_job_post_title(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post

    route = respx.patch(f"{HARVEST_BASE}/job_posts/10").mock(
        return_value=_ok({"id": 10, "title": "Lead Dev"})
    )
    result = await update_job_post(client, job_post_id=10, title="Lead Dev")
    assert result["title"] == "Lead Dev"
    assert _body(route) == {"title": "Lead Dev"}


@respx.mock
async def test_update_job_post_location_replaces_locations(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post

    respx.get(f"{HARVEST_BASE}/job_post_locations").mock(return_value=_ok([
        {"id": 1, "job_post_id": 10, "type": "free_text"},
        {"id": 2, "job_post_id": 10, "type": "office"},
    ]))
    created = respx.post(f"{HARVEST_BASE}/job_post_locations").mock(
        return_value=_ok({"id": 5, "plain_text_location": "Berlin"}, 201)
    )
    del1 = respx.delete(f"{HARVEST_BASE}/job_post_locations/1").mock(
        return_value=_ok({"id": 1, "message": "deleted"})
    )
    del2 = respx.delete(f"{HARVEST_BASE}/job_post_locations/2").mock(
        return_value=_ok({"id": 2, "message": "deleted"})
    )
    result = await update_job_post(client, job_post_id=10, location="Berlin")
    assert _body(created) == {"job_post_id": 10, "type": "free_text", "value": "Berlin"}
    assert del1.called and del2.called
    assert result["location"]["id"] == 5
    assert result["removed_location_ids"] == [1, 2]


async def test_update_job_post_requires_a_field(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post

    result = await update_job_post(client, job_post_id=10)
    assert result["status_code"] == 422


@respx.mock
async def test_update_job_post_status(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import update_job_post_status

    route = respx.patch(f"{HARVEST_BASE}/job_posts/10").mock(
        return_value=_ok({"id": 10, "live": False})
    )
    await update_job_post_status(client, job_post_id=10, status="offline")
    assert _body(route) == {"job_application_status": "draft"}
    await update_job_post_status(client, job_post_id=10, status="live")
    assert _body(route) == {"job_application_status": "live"}
    bad = await update_job_post_status(client, job_post_id=10, status="paused")
    assert bad["status_code"] == 422


@respx.mock
async def test_add_and_remove_job_post_location(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_posts import add_job_post_location, remove_job_post_location

    add = respx.post(f"{HARVEST_BASE}/job_post_locations").mock(
        return_value=_ok({"id": 8, "office_id": 20}, 201)
    )
    rm = respx.delete(f"{HARVEST_BASE}/job_post_locations/8").mock(
        return_value=_ok({"id": 8, "message": "deleted"})
    )
    result = await add_job_post_location(client, job_post_id=10, value="20", type="office")
    assert result["id"] == 8
    assert _body(add) == {"job_post_id": 10, "type": "office", "value": "20"}
    removed = await remove_job_post_location(client, job_post_location_id=8)
    assert removed["message"] == "deleted"
    assert rm.called


# --- job_stages ---

@respx.mock
async def test_list_job_stages(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import list_job_stages

    route = respx.get(f"{HARVEST_BASE}/job_interview_stages").mock(
        return_value=_ok([{"id": 1, "name": "Application Review", "sort_order": 0}])
    )
    result = await list_job_stages(client, active=True)
    assert _params(route)["active"] == "true"
    assert result["items"][0]["name"] == "Application Review"


@respx.mock
async def test_list_job_stages_for_job_sorted_with_interviews(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import list_job_stages_for_job

    stages = respx.get(f"{HARVEST_BASE}/job_interview_stages").mock(return_value=_ok([
        {"id": 3, "job_id": 42, "name": "Onsite", "sort_order": 2, "active": True},
        {"id": 1, "job_id": 42, "name": "Application Review", "sort_order": 0, "active": True},
        {"id": 2, "job_id": 42, "name": "Phone Screen", "sort_order": 1, "active": True},
    ]))
    interviews = respx.get(f"{HARVEST_BASE}/job_interviews").mock(return_value=_ok([
        {"id": 31, "job_interview_stage_id": 3, "name": "Systems", "sort_order": 2},
        {"id": 30, "job_interview_stage_id": 3, "name": "Coding", "sort_order": 1},
        {"id": 20, "job_interview_stage_id": 2, "name": "Recruiter Call", "sort_order": 0,
         "scheduling_type": "needs_scheduling"},
    ]))
    result = await list_job_stages_for_job(client, job_id=42)
    assert _params(stages)["job_ids"] == "42"
    assert _params(stages)["active"] == "true"
    assert _params(interviews)["job_ids"] == "42"
    assert [s["name"] for s in result["items"]] == ["Application Review", "Phone Screen", "Onsite"]
    assert result["items"][0]["interviews"] == []
    assert [i["name"] for i in result["items"][2]["interviews"]] == ["Coding", "Systems"]
    assert result["total"] == 3


@respx.mock
async def test_list_job_stages_for_job_include_inactive(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import list_job_stages_for_job

    stages = respx.get(f"{HARVEST_BASE}/job_interview_stages").mock(return_value=_ok([]))
    result = await list_job_stages_for_job(client, job_id=42, include_inactive=True)
    assert "active" not in _params(stages)
    assert result["items"] == []


@respx.mock
async def test_get_job_stage(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_stages import get_job_stage

    stage = respx.get(f"{HARVEST_BASE}/job_interview_stages").mock(
        return_value=_ok([{"id": 5, "name": "Onsite", "job_id": 42}])
    )
    interviews = respx.get(f"{HARVEST_BASE}/job_interviews").mock(
        return_value=_ok([{"id": 50, "job_interview_stage_id": 5, "name": "Coding"}])
    )
    result = await get_job_stage(client, job_stage_id=5)
    assert _params(stage)["ids"] == "5"
    assert _params(interviews)["job_interview_stage_ids"] == "5"
    assert result["id"] == 5
    assert result["interviews"][0]["name"] == "Coding"


# --- job_openings ---

@respx.mock
async def test_list_job_openings(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import list_job_openings

    route = respx.get(f"{HARVEST_BASE}/openings").mock(return_value=_ok([
        {"id": 1, "job_id": 42, "open": True, "sort_order": 1},
    ]))
    result = await list_job_openings(client, job_id=42, status="open")
    params = _params(route)
    assert params["job_ids"] == "42"
    assert params["open"] == "true"
    assert result["items"][0]["status"] == "open"


@respx.mock
async def test_list_job_openings_closed_status_derived(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import list_job_openings

    route = respx.get(f"{HARVEST_BASE}/openings").mock(
        return_value=_ok([{"id": 2, "job_id": 42, "open": False}])
    )
    result = await list_job_openings(client, job_id=42, status="closed")
    assert _params(route)["open"] == "false"
    assert result["items"][0]["status"] == "closed"
    bad = await list_job_openings(client, job_id=42, status="filled")
    assert bad["status_code"] == 422


@respx.mock
async def test_get_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import get_job_opening

    route = respx.get(f"{HARVEST_BASE}/openings").mock(
        return_value=_ok([{"id": 1, "job_id": 42, "open": True}])
    )
    result = await get_job_opening(client, job_id=42, opening_id=1)
    assert _params(route)["ids"] == "1"
    assert result["id"] == 1
    assert result["status"] == "open"
    wrong = await get_job_opening(client, job_id=43, opening_id=1)
    assert wrong["status_code"] == 404


@respx.mock
async def test_create_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import create_job_opening

    route = respx.post(f"{HARVEST_BASE}/openings").mock(
        return_value=_ok({"id": 7, "job_id": 42, "open": True}, 201)
    )
    result = await create_job_opening(
        client, job_id=42, opening_id="REQ-1", custom_fields=[{"id": 3, "value": 1}]
    )
    assert result["id"] == 7
    assert _body(route) == {
        "job_id": 42, "opening_id": "REQ-1",
        "custom_fields": [{"custom_field_id": 3, "value": 1}],
    }


@respx.mock
async def test_create_job_opening_closed(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import create_job_opening

    respx.post(f"{HARVEST_BASE}/openings").mock(
        return_value=_ok({"id": 7, "job_id": 42, "open": True}, 201)
    )
    close = respx.patch(f"{HARVEST_BASE}/openings/7").mock(
        return_value=_ok({"id": 7, "job_id": 42, "open": False})
    )
    result = await create_job_opening(client, job_id=42, status="closed", close_reason_id=9)
    assert _body(close) == {"job_id": 42, "status": "closed", "close_reason_id": 9}
    assert result["open"] is False


@respx.mock
async def test_update_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import update_job_opening

    route = respx.patch(f"{HARVEST_BASE}/openings/1").mock(
        return_value=_ok({"id": 1, "open": False})
    )
    result = await update_job_opening(
        client, job_id=42, opening_id=1, status="closed", close_reason_id=4
    )
    assert result["open"] is False
    assert _body(route) == {"job_id": 42, "status": "closed", "close_reason_id": 4}


@respx.mock
async def test_delete_job_opening(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import delete_job_opening

    respx.get(f"{HARVEST_BASE}/openings").mock(return_value=_ok([{"id": 1, "job_id": 42}]))
    route = respx.delete(f"{HARVEST_BASE}/openings/1").mock(
        return_value=_ok({"id": 1, "message": "deleted"})
    )
    result = await delete_job_opening(client, job_id=42, opening_id=1)
    assert result["message"] == "deleted"
    route.reset()
    wrong = await delete_job_opening(client, job_id=43, opening_id=1)
    assert wrong["status_code"] == 404
    assert not route.called


@respx.mock
async def test_bulk_openings(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.job_openings import (
        bulk_create_job_openings,
        bulk_delete_job_openings,
        bulk_update_job_openings,
        get_bulk_request_status,
    )

    accepted = {"bulk_action_uuid": "u-1", "status": "building", "status_url": "/x"}
    post = respx.post(f"{HARVEST_BASE}/openings/bulk").mock(return_value=_ok(accepted, 202))
    patch = respx.patch(f"{HARVEST_BASE}/openings/bulk").mock(return_value=_ok(accepted, 202))
    delete = respx.delete(f"{HARVEST_BASE}/openings/bulk").mock(return_value=_ok(accepted, 202))
    status = respx.get(f"{HARVEST_BASE}/bulk_requests/u-1").mock(
        return_value=_ok({"bulk_action_uuid": "u-1", "status": "completed", "success_count": 2})
    )

    r1 = await bulk_create_job_openings(
        client, openings=[{"job_id": 42}, {"job_id": 42, "custom_fields": [{"id": 1, "value": 2}]}]
    )
    assert r1["bulk_action_uuid"] == "u-1"
    assert _body(post)["data"][1]["custom_fields"] == [{"custom_field_id": 1, "value": 2}]

    await bulk_update_job_openings(
        client, openings=[{"id": 1, "status": "closed"}], callback_url="https://cb"
    )
    assert _body(patch) == {"data": [{"id": 1, "status": "closed"}], "callback_url": "https://cb"}

    await bulk_delete_job_openings(client, opening_ids=[1, 2])
    assert _body(delete) == {"data": [1, 2]}

    s = await get_bulk_request_status(client, bulk_action_uuid="u-1")
    assert s["status"] == "completed"
    assert status.called

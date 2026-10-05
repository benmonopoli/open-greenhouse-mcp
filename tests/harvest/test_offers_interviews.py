"""Tests for harvest/offers.py, scorecards.py, interviews.py (Harvest v3)."""
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


# --- offers ---

@respx.mock
async def test_list_offers(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import list_offers

    route = respx.get(f"{HARVEST_BASE}/offers").mock(
        return_value=_ok([{"id": 1, "status": "Created", "version": 1}])
    )
    result = await list_offers(
        client, created_after="2026-01-01T00:00:00Z", created_before="2026-02-01T00:00:00Z",
        job_id=42, status="Accepted",
    )
    params = _params(route)
    assert params["created_at[gte]"] == "2026-01-01T00:00:00Z"
    assert params["created_at[lt]"] == "2026-02-01T00:00:00Z"
    assert params["job_ids"] == "42"
    assert params["status"] == "Accepted"
    assert "current_only" not in params
    assert result["items"][0]["status"] == "Created"


@respx.mock
async def test_list_offers_current_only(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import list_offers

    route = respx.get(f"{HARVEST_BASE}/offers").mock(return_value=_ok([]))
    await list_offers(client, current_only=True)
    assert _params(route)["current_only"] == "true"


@respx.mock
async def test_list_offers_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import list_offers_for_application

    route = respx.get(f"{HARVEST_BASE}/offers").mock(return_value=_ok([
        {"id": 2, "version": 1, "status": "Deprecated"},
        {"id": 3, "version": 2, "status": "Created"},
    ]))
    result = await list_offers_for_application(client, application_id=10)
    assert _params(route)["application_ids"] == "10"
    assert [o["id"] for o in result["items"]] == [3, 2]


@respx.mock
async def test_get_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import get_offer

    route = respx.get(f"{HARVEST_BASE}/offers").mock(
        return_value=_ok([{"id": 1, "status": "Accepted"}])
    )
    result = await get_offer(client, offer_id=1)
    assert _params(route)["ids"] == "1"
    assert result["id"] == 1


@respx.mock
async def test_get_current_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import get_current_offer

    route = respx.get(f"{HARVEST_BASE}/offers").mock(return_value=_ok([
        {"id": 3, "version": 2, "status": "Created", "application_id": 10},
    ]))
    result = await get_current_offer(client, application_id=10)
    params = _params(route)
    assert params["application_ids"] == "10"
    assert params["current_only"] == "true"
    assert result["id"] == 3


@respx.mock
async def test_get_current_offer_none(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import get_current_offer

    respx.get(f"{HARVEST_BASE}/offers").mock(return_value=_ok([]))
    result = await get_current_offer(client, application_id=10)
    assert result["status_code"] == 404


@respx.mock
async def test_update_current_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import update_current_offer

    respx.get(f"{HARVEST_BASE}/offers").mock(
        return_value=_ok([{"id": 3, "version": 2, "application_id": 10}])
    )
    route = respx.patch(f"{HARVEST_BASE}/offers/3").mock(
        return_value=_ok({"id": 3, "starts_on": "2026-01-01"})
    )
    result = await update_current_offer(
        client, application_id=10, starts_at="2026-01-01",
        custom_fields=[{"id": 5, "value": 100000}],
    )
    assert result["starts_on"] == "2026-01-01"
    assert _body(route) == {
        "starts_on": "2026-01-01",
        "custom_fields": [{"custom_field_id": 5, "value": 100000}],
    }


@respx.mock
async def test_update_current_offer_no_offer(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.offers import update_current_offer

    respx.get(f"{HARVEST_BASE}/offers").mock(return_value=_ok([]))
    route = respx.patch(url__regex=rf"{HARVEST_BASE}/offers/\d+").mock(return_value=_ok({}))
    result = await update_current_offer(client, application_id=10, starts_at="2026-01-01")
    assert result["status_code"] == 404
    assert not route.called


# --- scorecards ---

SCORECARD = {
    "id": 5, "application_id": 10, "interview_kit_id": 70, "interviewer_id": 100,
    "submitter_id": 100, "candidate_rating": "yes", "status": "complete",
    "notes": "Solid", "submitted_at": "2026-03-01T10:00:00Z",
}


def _mock_scorecard_children() -> dict[str, respx.Route]:
    return {
        "attrs": respx.get(f"{HARVEST_BASE}/scorecard_candidate_attributes").mock(
            return_value=_ok([
                {"id": 1, "scorecard_id": 5, "job_candidate_attribute_id": 900,
                 "candidate_attribute_rating": "strong_yes", "note": "great"},
                {"id": 2, "scorecard_id": 5, "job_candidate_attribute_id": 901,
                 "candidate_attribute_rating": "no", "note": None},
            ])
        ),
        "answers": respx.get(f"{HARVEST_BASE}/scorecard_question_answers").mock(
            return_value=_ok([
                {"id": 11, "scorecard_id": 5, "scorecard_question_id": 801,
                 "answer": None, "boolean_value": True, "value": True},
                {"id": 10, "scorecard_id": 5, "scorecard_question_id": 800,
                 "answer": "Knows Python", "boolean_value": None, "value": "Knows Python"},
                {"id": 12, "scorecard_id": 5, "scorecard_question_id": 802,
                 "answer": None, "boolean_value": None, "value": [600, 601]},
            ])
        ),
        "users": respx.get(f"{HARVEST_BASE}/users").mock(
            return_value=_ok([{"id": 100, "name": "Ivy Interviewer", "primary_email": "i@x.com"}])
        ),
        "kits": respx.get(f"{HARVEST_BASE}/interview_kits").mock(
            return_value=_ok([{"id": 70, "job_interview_id": 50}])
        ),
        "job_attrs": respx.get(f"{HARVEST_BASE}/job_candidate_attributes").mock(
            return_value=_ok([
                {"id": 900, "name": "Python", "sort_order": 1},
                {"id": 901, "name": "Communication", "sort_order": 2},
            ])
        ),
        "questions": respx.get(f"{HARVEST_BASE}/scorecard_questions").mock(
            return_value=_ok([
                {"id": 800, "question": "Strengths?", "answer_type": "text", "sort_order": 1},
                {"id": 801, "question": "Hire?", "answer_type": "yes_no", "sort_order": 2},
                {"id": 802, "question": "Areas", "answer_type": "multi_select",
                 "sort_order": 3},
            ])
        ),
        "options": respx.get(f"{HARVEST_BASE}/scorecard_question_options").mock(
            return_value=_ok([{"id": 600, "name": "Backend"}, {"id": 601, "name": "Infra"}])
        ),
        "slots": respx.get(f"{HARVEST_BASE}/job_interviews").mock(
            return_value=_ok([{"id": 50, "name": "Technical Interview"}])
        ),
    }


def _assert_hydrated(sc: dict) -> None:
    assert sc["overall_recommendation"] == "yes"
    assert sc["interviewer"] == {"id": 100, "name": "Ivy Interviewer", "email": "i@x.com"}
    assert sc["submitted_by"]["id"] == 100
    assert sc["interview"] == "Technical Interview"
    assert sc["interview_step"] == {"id": 50, "name": "Technical Interview"}
    assert sc["attributes"] == [
        {"id": 900, "name": "Python", "rating": "strong_yes", "note": "great"},
        {"id": 901, "name": "Communication", "rating": "no", "note": None},
    ]
    assert sc["ratings"] == {"strong_yes": ["Python"], "no": ["Communication"]}
    assert [(q["question"], q["answer"]) for q in sc["questions"]] == [
        ("Strengths?", "Knows Python"), ("Hire?", "Yes"), ("Areas", "Backend, Infra"),
    ]


@respx.mock
async def test_list_scorecards_hydrated(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import list_scorecards

    route = respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([dict(SCORECARD)]))
    children = _mock_scorecard_children()
    result = await list_scorecards(client, created_after="2026-01-01T00:00:00Z", status="complete")
    params = _params(route)
    assert params["created_at[gte]"] == "2026-01-01T00:00:00Z"
    assert params["status"] == "complete"
    assert _params(children["attrs"])["scorecard_ids"] == "5"
    assert _params(children["options"])["ids"] == "600,601"
    _assert_hydrated(result["items"][0])
    assert "warnings" not in result


@respx.mock
async def test_list_scorecards_without_details(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import list_scorecards

    respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([dict(SCORECARD)]))
    children = _mock_scorecard_children()
    result = await list_scorecards(client, include_details=False)
    assert result["items"][0]["candidate_rating"] == "yes"
    assert not children["attrs"].called


@respx.mock
async def test_list_scorecards_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import list_scorecards_for_application

    route = respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([dict(SCORECARD)]))
    _mock_scorecard_children()
    result = await list_scorecards_for_application(client, application_id=10)
    assert _params(route)["application_ids"] == "10"
    _assert_hydrated(result["items"][0])


@respx.mock
async def test_get_scorecard(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import get_scorecard

    route = respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([dict(SCORECARD)]))
    _mock_scorecard_children()
    result = await get_scorecard(client, scorecard_id=5)
    assert _params(route)["ids"] == "5"
    _assert_hydrated(result)


@respx.mock
async def test_get_scorecard_degrades_when_lookup_forbidden(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import get_scorecard

    respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([dict(SCORECARD)]))
    _mock_scorecard_children()
    respx.get(f"{HARVEST_BASE}/users").mock(return_value=_ok({}, 403))
    result = await get_scorecard(client, scorecard_id=5)
    assert result["interviewer"] == {"id": 100, "name": None, "email": None}
    assert any("/users" in w for w in result["warnings"])
    assert result["attributes"][0]["name"] == "Python"


@respx.mock
async def test_get_scorecard_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.scorecards import get_scorecard

    respx.get(f"{HARVEST_BASE}/scorecards").mock(return_value=_ok([]))
    result = await get_scorecard(client, scorecard_id=5)
    assert result["status_code"] == 404


# --- interviews ---

INTERVIEW = {
    "id": 1, "application_id": 10, "job_id": 42, "job_interview_id": 50,
    "starts_at": "2026-05-01T10:00:00Z", "ends_at": "2026-05-01T11:00:00Z",
    "status": "scheduled", "organizer_id": 101,
}


def _mock_interview_children() -> dict[str, respx.Route]:
    return {
        "panel": respx.get(f"{HARVEST_BASE}/interviewers").mock(return_value=_ok([
            {"id": 9, "interview_id": 1, "user_id": 100, "scorecard_id": 5,
             "email": "i@x.com", "response_status": "accepted"},
        ])),
        "slots": respx.get(f"{HARVEST_BASE}/job_interviews").mock(
            return_value=_ok([{"id": 50, "name": "Technical Interview"}])
        ),
        "users": respx.get(f"{HARVEST_BASE}/users").mock(return_value=_ok([
            {"id": 100, "name": "Ivy Interviewer", "primary_email": "i@x.com"},
            {"id": 101, "name": "Olly Organizer", "primary_email": "o@x.com"},
        ])),
    }


def _assert_interview_hydrated(iv: dict) -> None:
    assert iv["interview"] == {"id": 50, "name": "Technical Interview"}
    assert iv["interviewers"] == [{
        "id": 100, "name": "Ivy Interviewer", "email": "i@x.com",
        "response_status": "accepted", "scorecard_id": 5,
    }]
    assert iv["organizer"]["name"] == "Olly Organizer"


@respx.mock
async def test_list_interviews(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import list_interviews

    route = respx.get(f"{HARVEST_BASE}/interviews").mock(return_value=_ok([dict(INTERVIEW)]))
    children = _mock_interview_children()
    result = await list_interviews(
        client, starts_after="2026-05-01T00:00:00Z", job_id=42, status="scheduled"
    )
    params = _params(route)
    assert params["starts_at[gte]"] == "2026-05-01T00:00:00Z"
    assert params["job_ids"] == "42"
    assert params["status"] == "scheduled"
    assert _params(children["panel"])["interview_ids"] == "1"
    assert _params(children["users"])["ids"] == "100,101"
    _assert_interview_hydrated(result["items"][0])


@respx.mock
async def test_list_interviews_created_filter_without_details(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import list_interviews

    route = respx.get(f"{HARVEST_BASE}/interviews").mock(return_value=_ok([dict(INTERVIEW)]))
    children = _mock_interview_children()
    result = await list_interviews(
        client, created_after="2026-01-01T00:00:00Z", include_details=False
    )
    assert _params(route)["created_at[gte]"] == "2026-01-01T00:00:00Z"
    assert "interviewers" not in result["items"][0]
    assert not children["panel"].called


@respx.mock
async def test_list_interviews_for_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import list_interviews_for_application

    route = respx.get(f"{HARVEST_BASE}/interviews").mock(return_value=_ok([dict(INTERVIEW)]))
    _mock_interview_children()
    result = await list_interviews_for_application(client, application_id=10)
    assert _params(route)["application_ids"] == "10"
    _assert_interview_hydrated(result["items"][0])
    assert result["total"] == 1


@respx.mock
async def test_get_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import get_interview

    route = respx.get(f"{HARVEST_BASE}/interviews").mock(return_value=_ok([dict(INTERVIEW)]))
    _mock_interview_children()
    result = await get_interview(client, interview_id=1)
    assert _params(route)["ids"] == "1"
    assert result["id"] == 1
    _assert_interview_hydrated(result)


@respx.mock
async def test_create_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import create_interview

    route = respx.post(f"{HARVEST_BASE}/interviews").mock(
        return_value=_ok({"id": 9, "status": "scheduled"}, 201)
    )
    result = await create_interview(
        client,
        application_id=10,
        interview_id=50,
        interviewer_ids=[100, 101],
        start="2026-05-01T10:00:00Z",
        end="2026-05-01T11:00:00Z",
        location="Room 1",
    )
    assert result["id"] == 9
    body = _body(route)
    assert body["application_id"] == 10
    assert body["job_interview_id"] == 50
    assert body["starts_at"] == "2026-05-01T10:00:00Z"
    assert body["ends_at"] == "2026-05-01T11:00:00Z"
    assert body["interviewers"] == [
        {"user_id": 100, "response_status": "needs_action"},
        {"user_id": 101, "response_status": "needs_action"},
    ]
    assert body["external_event_id"].startswith("greenhouse-mcp-")
    assert body["location"] == "Room 1"


@respx.mock
async def test_create_interview_with_event_id(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import create_interview

    route = respx.post(f"{HARVEST_BASE}/interviews").mock(return_value=_ok({"id": 9}, 201))
    await create_interview(
        client, application_id=10, interview_id=50, interviewer_ids=[100],
        start="2026-05-01T10:00:00Z", end="2026-05-01T11:00:00Z", external_event_id="gcal-1",
    )
    assert _body(route)["external_event_id"] == "gcal-1"


@respx.mock
async def test_update_interview_time(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import update_interview

    route = respx.patch(f"{HARVEST_BASE}/interviews/1").mock(
        return_value=_ok({"id": 1, "starts_at": "2026-05-02T10:00:00Z"})
    )
    result = await update_interview(client, interview_id=1, start="2026-05-02T10:00:00Z")
    assert result["starts_at"] == "2026-05-02T10:00:00Z"
    assert _body(route) == {"starts_at": "2026-05-02T10:00:00Z"}


@respx.mock
async def test_update_interview_panel_keeps_rsvp(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import update_interview

    panel = respx.get(f"{HARVEST_BASE}/interviewers").mock(return_value=_ok([
        {"id": 9, "interview_id": 1, "user_id": 100, "response_status": "accepted"},
    ]))
    route = respx.patch(f"{HARVEST_BASE}/interviews/1").mock(return_value=_ok({"id": 1}))
    await update_interview(client, interview_id=1, interviewer_ids=[100, 102])
    assert _params(panel)["interview_ids"] == "1"
    assert _body(route) == {"interviewers": [
        {"user_id": 100, "response_status": "accepted"},
        {"user_id": 102, "response_status": "needs_action"},
    ]}


@respx.mock
async def test_delete_interview(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.interviews import delete_interview

    respx.delete(f"{HARVEST_BASE}/interviews/1").mock(
        return_value=_ok({"id": 1, "message": "deleted"})
    )
    result = await delete_interview(client, interview_id=1)
    assert result["message"] == "deleted"

"""Tests for harvest/candidates.py, harvest/attachments.py and harvest/education.py (v3)."""
from __future__ import annotations

import json

import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient
from tests.conftest import HARVEST_BASE


def _cand(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": 42,
        "first_name": "Bob",
        "last_name": "Jones",
        "tags": ["referral"],
        "email_addresses": [{"value": "bob@example.com", "type": "personal"}],
        "custom_fields": {},
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


# ---------------------------------------------------------------------------
# list / get
# ---------------------------------------------------------------------------


@respx.mock
async def test_list_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand(id=1, first_name="Alice")])
    )
    result = await list_candidates(client)
    assert result["items"][0]["first_name"] == "Alice"
    assert result["has_next"] is False


@respx.mock
async def test_list_candidates_with_filters(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand(id=2)])
    )
    result = await list_candidates(
        client,
        email="alice@example.com",
        candidate_ids=[2, 3],
        tag="referral",
        updated_after="2026-09-01T00:00:00Z",
        updated_before="2026-10-01T00:00:00Z",
    )
    assert result["items"][0]["id"] == 2
    params = route.calls[0].request.url.params
    assert params["email"] == "alice@example.com"
    assert params["ids"] == "2,3"
    assert params["tag"] == "referral"
    assert params["updated_at[gte]"] == "2026-09-01T00:00:00Z"
    assert params["updated_at[lt]"] == "2026-10-01T00:00:00Z"
    assert "candidate_ids" not in params and "page" not in params


@respx.mock
async def test_list_candidates_created_filters_and_cursor(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )
    await list_candidates(client, created_after="2026-01-01T00:00:00Z")
    assert route.calls[0].request.url.params["created_at[gte]"] == "2026-01-01T00:00:00Z"
    await list_candidates(client, cursor="c1", created_after="2026-01-01T00:00:00Z")
    assert dict(route.calls[1].request.url.params) == {"cursor": "c1"}


async def test_list_candidates_rejects_created_and_updated(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import list_candidates

    result = await list_candidates(
        client, created_after="2026-01-01T00:00:00Z", updated_after="2026-01-01T00:00:00Z"
    )
    assert result["status_code"] == 400


@respx.mock
async def test_get_candidate_enriched(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import get_candidate

    cands = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand()])
    )
    apps = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "candidate_id": 42,
                    "job_id": 100,
                    "stage_name": "Onsite",
                    "job_interview_stage_id": 555,
                    "status": "in_process",
                }
            ],
        )
    )
    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 100, "name": "Backend Engineer"}])
    )
    atts = respx.get(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(
            200, json=[{"id": 7, "application_id": 1, "type": "resume", "url": "https://x"}]
        )
    )
    respx.get(f"{HARVEST_BASE}/candidate_educations").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 31,
                    "candidate_id": 42,
                    "school_name_custom_field_option_id": 501,
                    "degree_custom_field_option_id": 502,
                    "discipline_custom_field_option_id": None,
                }
            ],
        )
    )
    opts = respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
        return_value=httpx.Response(
            200, json=[{"id": 501, "name": "MIT"}, {"id": 502, "name": "Bachelor's"}]
        )
    )
    respx.get(f"{HARVEST_BASE}/candidate_employments").mock(
        return_value=httpx.Response(
            200, json=[{"id": 41, "candidate_id": 42, "company_name": "Acme", "title": "Eng"}]
        )
    )
    result = await get_candidate(client, candidate_id=42)
    assert result["id"] == 42
    assert cands.calls[0].request.url.params["ids"] == "42"
    assert apps.calls[0].request.url.params["candidate_ids"] == "42"
    assert atts.calls[0].request.url.params["candidate_ids"] == "42"
    assert result["applications"][0]["job_name"] == "Backend Engineer"
    assert result["applications"][0]["stage_name"] == "Onsite"
    assert result["attachments"][0]["type"] == "resume"
    edu = result["educations"][0]
    assert (edu["school_name"], edu["degree"], edu["discipline"]) == ("MIT", "Bachelor's", None)
    assert set(opts.calls[0].request.url.params["ids"].split(",")) == {"501", "502"}
    assert result["employments"][0]["company_name"] == "Acme"
    assert "warnings" not in result


@respx.mock
async def test_get_candidate_bare_and_partial_failures(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import get_candidate

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand()])
    )
    apps = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(403, json={})
    )
    for ep in ("attachments", "candidate_educations", "candidate_employments"):
        respx.get(f"{HARVEST_BASE}/{ep}").mock(return_value=httpx.Response(200, json=[]))

    bare = await get_candidate(client, candidate_id=42, include_related=False)
    assert "applications" not in bare
    assert not apps.called

    result = await get_candidate(client, candidate_id=42)
    assert result["applications"] == []
    assert any("/applications" in w for w in result["warnings"])


@respx.mock
async def test_get_candidate_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import get_candidate

    respx.get(f"{HARVEST_BASE}/candidates").mock(return_value=httpx.Response(200, json=[]))
    result = await get_candidate(client, candidate_id=9999)
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# create / update / delete / merge / anonymize / prospects
# ---------------------------------------------------------------------------


@respx.mock
async def test_create_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import create_candidate

    route = respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            201, json={"candidate": _cand(id=99, first_name="Carol"), "application": None}
        )
    )
    result = await create_candidate(
        client,
        first_name="Carol",
        last_name="Smith",
        company="Acme",
        email_addresses=[{"value": "carol@example.com", "type": "personal"}],
        custom_fields=[{"id": 5, "value": "x"}, {"name_key": "level", "value": "senior"}],
    )
    assert result["candidate"]["id"] == 99
    assert _body(route) == {
        "first_name": "Carol",
        "last_name": "Smith",
        "company": "Acme",
        "email_addresses": [{"value": "carol@example.com", "type": "personal"}],
        "custom_fields": [
            {"custom_field_id": 5, "value": "x"},
            {"name_key": "level", "value": "senior"},
        ],
    }


@respx.mock
async def test_create_candidate_with_nested_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import create_candidate

    route = respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            201, json={"candidate": _cand(id=99), "application": {"id": 5, "job_id": 100}}
        )
    )
    result = await create_candidate(
        client, first_name="Carol", last_name="Smith", job_id=100, source_id=3, recruiter_id=8
    )
    assert result["application"]["id"] == 5
    assert _body(route)["application"] == {"job_id": 100, "source_id": 3, "recruiter_id": 8}


async def test_create_candidate_application_fields_need_job(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import create_candidate

    result = await create_candidate(client, first_name="A", last_name="B", source_id=3)
    assert result["status_code"] == 400
    assert "job_id" in result["error"]


@respx.mock
async def test_update_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import update_candidate

    route = respx.patch(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json=_cand(title="Engineer"))
    )
    result = await update_candidate(client, candidate_id=42, title="Engineer", tags=["a", "b"])
    assert result["title"] == "Engineer"
    assert _body(route) == {"title": "Engineer", "tags": ["a", "b"]}


@respx.mock
async def test_delete_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import delete_candidate

    respx.delete(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "message": "deleted"})
    )
    result = await delete_candidate(client, candidate_id=42)
    assert result["id"] == 42


@respx.mock
async def test_merge_candidates(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import merge_candidates

    route = respx.post(f"{HARVEST_BASE}/candidates/1/merge").mock(
        return_value=httpx.Response(200, json=_cand(id=1))
    )
    result = await merge_candidates(client, primary_candidate_id=1, duplicate_candidate_id=2)
    assert result["id"] == 1
    assert _body(route) == {"secondary_candidate_id": 2}


@respx.mock
async def test_anonymize_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import anonymize_candidate

    route = respx.patch(f"{HARVEST_BASE}/candidates/42/anonymize").mock(
        return_value=httpx.Response(200, json=_cand(first_name=None))
    )
    result = await anonymize_candidate(client, candidate_id=42, fields=["full_name", "emails"])
    assert result["id"] == 42
    assert _body(route) == {"fields": ["full_name", "emails"]}


async def test_anonymize_candidate_requires_fields(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import anonymize_candidate

    result = await anonymize_candidate(client, candidate_id=42, fields=[])
    assert result["status_code"] == 400


@respx.mock
async def test_add_prospect(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_prospect

    route = respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(
            201, json={"candidate": _cand(id=50), "application": {"id": 6, "prospect": True}}
        )
    )
    result = await add_prospect(
        client,
        first_name="Pat",
        last_name="Lee",
        prospect_pool_id=1,
        prospect_stage_id=2,
        prospect_owner_id=3,
        job_ids=[100],
    )
    assert result["application"]["prospect"] is True
    body = _body(route)
    assert "is_prospect" not in body
    assert body["application"] == {
        "prospect": True,
        "prospect_pool_id": 1,
        "prospect_pool_stage_id": 2,
        "prospect_owner_id": 3,
        "job_ids": [100],
    }


# ---------------------------------------------------------------------------
# educations / employments
# ---------------------------------------------------------------------------


@respx.mock
async def test_add_education(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_education

    route = respx.post(f"{HARVEST_BASE}/candidate_educations").mock(
        return_value=httpx.Response(201, json={"id": 31, "candidate_id": 42})
    )
    result = await add_education(
        client, candidate_id=42, school_id=501, degree_id=502, start_date="2010-09-01"
    )
    assert result["id"] == 31
    assert _body(route) == {
        "candidate_id": 42,
        "school_name_custom_field_option_id": 501,
        "degree_custom_field_option_id": 502,
        "start_date": "2010-09-01",
    }


@respx.mock
async def test_remove_education(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_education

    lookup = respx.get(f"{HARVEST_BASE}/candidate_educations").mock(
        return_value=httpx.Response(200, json=[{"id": 31, "candidate_id": 42}])
    )
    route = respx.delete(f"{HARVEST_BASE}/candidate_educations/31").mock(
        return_value=httpx.Response(200, json={"id": 31, "message": "deleted"})
    )
    result = await remove_education(client, candidate_id=42, education_id=31)
    assert result["id"] == 31
    assert lookup.calls[0].request.url.params["ids"] == "31"
    assert route.called


@respx.mock
async def test_remove_education_wrong_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_education

    respx.get(f"{HARVEST_BASE}/candidate_educations").mock(
        return_value=httpx.Response(200, json=[{"id": 31, "candidate_id": 7}])
    )
    route = respx.delete(f"{HARVEST_BASE}/candidate_educations/31")
    result = await remove_education(client, candidate_id=42, education_id=31)
    assert result["status_code"] == 400
    assert not route.called


@respx.mock
async def test_add_employment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_employment

    route = respx.post(f"{HARVEST_BASE}/candidate_employments").mock(
        return_value=httpx.Response(201, json={"id": 41, "candidate_id": 42})
    )
    result = await add_employment(
        client, candidate_id=42, company_name="Acme", title="Eng", start_date="2020-01-01"
    )
    assert result["id"] == 41
    assert _body(route) == {
        "candidate_id": 42,
        "company_name": "Acme",
        "title": "Eng",
        "start_date": "2020-01-01",
    }


async def test_add_employment_requires_fields(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_employment

    result = await add_employment(client, candidate_id=42, company_name="Acme")
    assert result["status_code"] == 400
    assert "title" in result["error"] and "start_date" in result["error"]


@respx.mock
async def test_remove_employment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_employment

    respx.get(f"{HARVEST_BASE}/candidate_employments").mock(
        return_value=httpx.Response(200, json=[{"id": 41, "candidate_id": 42}])
    )
    route = respx.delete(f"{HARVEST_BASE}/candidate_employments/41").mock(
        return_value=httpx.Response(200, json={"id": 41, "message": "deleted"})
    )
    result = await remove_employment(client, candidate_id=42, employment_id=41)
    assert result["id"] == 41
    assert route.called


@respx.mock
async def test_remove_employment_not_found(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import remove_employment

    respx.get(f"{HARVEST_BASE}/candidate_employments").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = await remove_employment(client, candidate_id=42, employment_id=41)
    assert result["status_code"] == 404


# ---------------------------------------------------------------------------
# attachments / notes
# ---------------------------------------------------------------------------


@respx.mock
async def test_add_attachment_picks_most_recent_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_attachment

    apps = respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "candidate_id": 42, "last_activity_at": "2026-01-01T00:00:00Z"},
                {"id": 2, "candidate_id": 42, "last_activity_at": "2026-09-01T00:00:00Z"},
            ],
        )
    )
    route = respx.post(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(201, json={"id": 77, "application_id": 2})
    )
    result = await add_attachment(
        client, candidate_id=42, filename="cv.pdf", type="resume", content="QUJD"
    )
    assert result["application_id"] == 2
    assert apps.calls[0].request.url.params["candidate_ids"] == "42"
    assert _body(route) == {
        "application_id": 2,
        "filename": "cv.pdf",
        "type": "resume",
        "content": "QUJD",
    }


@respx.mock
async def test_add_attachment_explicit_application(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_attachment

    apps = respx.get(f"{HARVEST_BASE}/applications")
    route = respx.post(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(201, json={"id": 78, "application_id": 5})
    )
    await add_attachment(
        client,
        candidate_id=42,
        application_id=5,
        filename="cl.pdf",
        type="cover_letter",
        url="https://x/cl.pdf",
        visibility="private",
    )
    assert not apps.called
    assert _body(route)["visibility"] == "private"


@respx.mock
async def test_add_attachment_no_applications(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_attachment

    respx.get(f"{HARVEST_BASE}/applications").mock(return_value=httpx.Response(200, json=[]))
    result = await add_attachment(
        client, candidate_id=42, filename="cv.pdf", type="resume", content="QUJD"
    )
    assert result["status_code"] == 400


@respx.mock
async def test_add_note_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_note_to_candidate

    route = respx.post(f"{HARVEST_BASE}/notes").mock(
        return_value=httpx.Response(201, json={"id": 5, "type": "NOTE", "body": "Great call"})
    )
    result = await add_note_to_candidate(client, candidate_id=42, body="Great call")
    assert result["id"] == 5
    assert _body(route) == {
        "candidate_id": 42,
        "body": "Great call",
        "note_type": "NOTE",
        "visibility": "private",
    }


@respx.mock
async def test_add_email_note_to_candidate(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.candidates import add_email_note_to_candidate

    route = respx.post(f"{HARVEST_BASE}/notes").mock(
        return_value=httpx.Response(201, json={"id": 6, "type": "EMAIL"})
    )
    result = await add_email_note_to_candidate(
        client,
        candidate_id=42,
        to="bob@example.com",
        from_="recruiter@co.com",
        subject="Hello",
        body="Hi Bob",
    )
    assert result["id"] == 6
    assert _body(route) == {
        "candidate_id": 42,
        "note_type": "EMAIL",
        "subject": "Hello",
        "body": "Hi Bob",
        "email_to": ["bob@example.com"],
        "email_from": ["recruiter@co.com"],
        "email_cc": [],
        "visibility": "public",
    }


def test_write_tools_detected() -> None:
    from greenhouse_mcp.harvest import attachments, candidates, education

    for name in (
        "create_candidate",
        "add_attachment",
        "remove_education",
        "remove_employment",
        "add_note_to_candidate",
        "merge_candidates",
        "anonymize_candidate",
    ):
        assert _is_write_tool(getattr(candidates, name)), name
    for fn in (
        candidates.get_candidate,
        candidates.list_candidates,
        attachments.read_candidate_resume,
        education.list_schools,
    ):
        assert not _is_write_tool(fn), fn.__name__


# ---------------------------------------------------------------------------
# attachments.py
# ---------------------------------------------------------------------------


@respx.mock
async def test_read_candidate_resume(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.attachments import read_candidate_resume

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand()])
    )
    atts = respx.get(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "application_id": 10,
                    "type": "resume",
                    "filename": "old.txt",
                    "url": "https://files.example/old",
                    "created_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "application_id": 11,
                    "type": "resume",
                    "filename": "new.txt",
                    "url": "https://files.example/new",
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {"id": 3, "application_id": 11, "type": "cover_letter", "url": "https://c"},
            ],
        )
    )
    respx.get("https://files.example/new").mock(
        return_value=httpx.Response(200, text="Resume text", headers={"content-type": "text/plain"})
    )
    result = await read_candidate_resume(client, candidate_id=42)
    assert result["content"] == "Resume text"
    assert result["filename"] == "new.txt"
    assert result["application_id"] == 11
    assert result["candidate_name"] == "Bob Jones"
    assert atts.calls[0].request.url.params["candidate_ids"] == "42"


@respx.mock
async def test_read_candidate_resume_none(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.attachments import read_candidate_resume

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[_cand()])
    )
    respx.get(f"{HARVEST_BASE}/attachments").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "type": "cover_letter"}])
    )
    result = await read_candidate_resume(client, candidate_id=42)
    assert result["error"] == "No resume found for this candidate."
    assert result["attachment_types"] == ["cover_letter"]


@respx.mock
async def test_read_candidate_resume_candidate_missing(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.attachments import read_candidate_resume

    respx.get(f"{HARVEST_BASE}/candidates").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{HARVEST_BASE}/attachments").mock(return_value=httpx.Response(200, json=[]))
    result = await read_candidate_resume(client, candidate_id=42)
    assert result["status_code"] == 404


@respx.mock
async def test_download_attachment(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.attachments import download_attachment

    respx.get("https://files.example/a.pdf").mock(
        return_value=httpx.Response(
            200, content=b"%PDF", headers={"content-type": "application/pdf"}
        )
    )
    result = await download_attachment(client, url="https://files.example/a.pdf")
    assert result["content_base64"] == "JVBERg=="
    assert result["size_bytes"] == 4


# ---------------------------------------------------------------------------
# education.py
# ---------------------------------------------------------------------------


@respx.mock
async def test_list_degrees_disciplines_schools(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.education import list_degrees, list_disciplines, list_schools

    route = respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Bachelor's"}])
    )
    result = await list_degrees(client)
    assert result["items"][0]["name"] == "Bachelor's"
    params = route.calls[0].request.url.params
    assert params["custom_field_key"] == "degree"
    assert params["active"] == "true"
    assert params["per_page"] == "500"

    await list_disciplines(client)
    assert route.calls[1].request.url.params["custom_field_key"] == "discipline"
    await list_schools(client, per_page=50)
    assert route.calls[2].request.url.params["custom_field_key"] == "school_name"

    # cached: a repeat call doesn't hit the API; force_refresh does
    await list_degrees(client)
    assert route.call_count == 3
    await list_degrees(client, force_refresh=True)
    assert route.call_count == 4


@respx.mock
async def test_list_schools_cursor(client: GreenhouseClient) -> None:
    from greenhouse_mcp.harvest.education import list_schools

    route = respx.get(f"{HARVEST_BASE}/custom_field_options").mock(
        return_value=httpx.Response(200, json=[])
    )
    await list_schools(client, cursor="next1")
    assert dict(route.calls[0].request.url.params) == {"cursor": "next1"}

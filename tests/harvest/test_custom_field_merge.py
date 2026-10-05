"""Custom-field updates must not wipe a record's other custom fields (v3 PATCH replaces
the whole collection), and must not write at all if the current values can't be read."""
from __future__ import annotations

import json

import respx

from greenhouse_mcp.harvest._custom_field_merge import merge_with_current
from tests.conftest import HARVEST_BASE

CURRENT = {
    "employment_type": {"name": "Employment Type", "type": "single_select", "value": "Full-time"},
    "salary_band": {"name": "Salary band", "type": "short_text", "value": "B2"},
    "empty_field": {"name": "Empty", "type": "short_text", "value": None},
}


def test_merge_keeps_other_fields_and_overrides_by_name_key():
    merged = merge_with_current(CURRENT, [{"name_key": "salary_band", "value": "B3"}], {})
    assert {"name_key": "employment_type", "value": "Full-time"} in merged
    assert {"name_key": "salary_band", "value": "B3"} in merged
    assert all(m.get("name_key") != "empty_field" for m in merged)
    assert len(merged) == 2


def test_merge_maps_custom_field_ids_and_v1_ids():
    merged = merge_with_current(
        CURRENT,
        [{"custom_field_id": 11, "value": "Contract"}, {"id": 12, "value": "B4"}],
        {11: "employment_type", 12: "salary_band"},
    )
    assert sorted(merged, key=lambda m: m["name_key"]) == [
        {"name_key": "employment_type", "value": "Contract"},
        {"name_key": "salary_band", "value": "B4"},
    ]


def test_merge_keeps_unknown_ids_as_given():
    merged = merge_with_current({}, [{"custom_field_id": 99, "value": "x"}], {})
    assert merged == [{"custom_field_id": 99, "value": "x"}]


@respx.mock
async def test_update_candidate_sends_full_custom_field_list(client):
    from greenhouse_mcp.harvest.candidates import update_candidate

    respx.get(f"{HARVEST_BASE}/candidates", params={"ids": "5"}).respond(
        200, json=[{"id": 5, "custom_fields": CURRENT}]
    )
    respx.get(f"{HARVEST_BASE}/custom_fields", params={"ids": "12"}).respond(
        200, json=[{"id": 12, "name_key": "salary_band"}]
    )
    patch = respx.patch(f"{HARVEST_BASE}/candidates/5").respond(200, json={"id": 5})
    await update_candidate(client, candidate_id=5, custom_fields=[{"id": 12, "value": "B3"}])
    sent = json.loads(patch.calls[0].request.content)["custom_fields"]
    assert {"name_key": "employment_type", "value": "Full-time"} in sent
    assert {"name_key": "salary_band", "value": "B3"} in sent


@respx.mock
async def test_update_candidate_does_not_write_if_current_unreadable(client):
    from greenhouse_mcp.harvest.candidates import update_candidate

    respx.get(f"{HARVEST_BASE}/candidates").respond(403, json={})
    patch = respx.patch(f"{HARVEST_BASE}/candidates/5").respond(200, json={"id": 5})
    result = await update_candidate(
        client, candidate_id=5, custom_fields=[{"name_key": "salary_band", "value": "B3"}]
    )
    assert result["status_code"] == 403
    assert patch.call_count == 0


@respx.mock
async def test_update_job_merges_custom_fields(client):
    from greenhouse_mcp.harvest.jobs import update_job

    respx.get(f"{HARVEST_BASE}/jobs", params={"ids": "7"}).respond(
        200, json=[{"id": 7, "custom_fields": CURRENT}]
    )
    patch = respx.patch(f"{HARVEST_BASE}/jobs/7").respond(200, json={"id": 7})
    await update_job(
        client, job_id=7, custom_fields=[{"name_key": "employment_type", "value": "Part-time"}]
    )
    sent = json.loads(patch.calls[0].request.content)["custom_fields"]
    assert {"name_key": "employment_type", "value": "Part-time"} in sent
    assert {"name_key": "salary_band", "value": "B2"} in sent


@respx.mock
async def test_update_job_opening_merges_custom_fields(client):
    from greenhouse_mcp.harvest.job_openings import update_job_opening

    respx.get(f"{HARVEST_BASE}/openings", params={"ids": "3"}).respond(
        200, json=[{"id": 3, "custom_fields": CURRENT}]
    )
    patch = respx.patch(f"{HARVEST_BASE}/openings/3").respond(200, json={"id": 3})
    await update_job_opening(
        client, job_id=7, opening_id=3, custom_fields=[{"name_key": "salary_band", "value": "C"}]
    )
    sent = json.loads(patch.calls[0].request.content)["custom_fields"]
    assert len(sent) == 2
    assert {"name_key": "salary_band", "value": "C"} in sent


@respx.mock
async def test_bulk_update_job_openings_merges_each_opening(client):
    from greenhouse_mcp.harvest.job_openings import bulk_update_job_openings

    respx.get(f"{HARVEST_BASE}/openings", params={"ids": "3"}).respond(
        200, json=[{"id": 3, "custom_fields": CURRENT}]
    )
    patch = respx.patch(f"{HARVEST_BASE}/openings/bulk").respond(
        202, json={"bulk_action_uuid": "u"}
    )
    await bulk_update_job_openings(
        client,
        openings=[
            {"id": 3, "custom_fields": [{"name_key": "salary_band", "value": "C"}]},
            {"id": 4, "status": "closed"},
        ],
    )
    data = json.loads(patch.calls[0].request.content)["data"]
    assert len(data[0]["custom_fields"]) == 2
    assert "custom_fields" not in data[1]


def test_merge_ignores_non_dict_current_values():
    assert merge_with_current({"x": "bad"}, [], {}) == []


async def test_get_ids_route_unused_when_all_name_keys(client):
    # No /custom_fields lookup when every update already uses name_key.
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{HARVEST_BASE}/candidates").respond(
            200, json=[{"id": 1, "custom_fields": {}}]
        )
        lookup = router.get(f"{HARVEST_BASE}/custom_fields").respond(200, json=[])
        router.patch(f"{HARVEST_BASE}/candidates/1").respond(200, json={})
        from greenhouse_mcp.harvest.candidates import update_candidate

        await update_candidate(
            client, candidate_id=1, custom_fields=[{"name_key": "a", "value": 1}]
        )
        assert lookup.call_count == 0

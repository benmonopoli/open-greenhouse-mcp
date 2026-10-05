"""Harvest API — Hiring Team tools (4 tools).

v3 stores the hiring team as rows: hiring managers in ``/job_hiring_managers`` and
recruiters, coordinators and sourcers in ``/job_owners`` (with a ``type``). There is
no single replace call, so writes are expanded into per-member creates and deletes.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient

# hiring team key -> job_owners type (None = job_hiring_managers)
_ROLES: dict[str, str | None] = {
    "hiring_managers": None,
    "recruiters": "recruiter",
    "coordinators": "coordinator",
    "sourcers": "sourcer",
}


def _endpoint(role: str) -> str:
    return "/job_hiring_managers" if _ROLES[role] is None else "/job_owners"


async def _team_rows(client: GreenhouseClient, job_id: int) -> dict[str, Any]:
    """Current hiring-team rows for a job, grouped by role key."""
    params = {"job_ids": [job_id], "per_page": 500}
    managers = await client.harvest_get("/job_hiring_managers", params=params, paginate="all")
    if client._is_error(managers):
        return managers
    owners = await client.harvest_get("/job_owners", params=params, paginate="all")
    if client._is_error(owners):
        return owners
    team: dict[str, list[dict[str, Any]]] = {role: [] for role in _ROLES}
    team["hiring_managers"] = list(managers.get("items", []))
    by_type = {t: role for role, t in _ROLES.items() if t}
    for row in owners.get("items", []):
        role = by_type.get(row.get("type"))
        if role:
            team[role].append(row)
    return team


def _member_user_id(member: dict[str, Any]) -> Any:
    return member.get("user_id", member.get("id"))


def _add_body(job_id: int, role: str, member: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {"job_id": job_id, "user_id": _member_user_id(member)}
    owner_type = _ROLES[role]
    if owner_type is not None:
        body["type"] = owner_type
        if owner_type in ("recruiter", "coordinator") and member.get("candidate_responsibility"):
            body["candidate_responsibility"] = member["candidate_responsibility"]
    return body


async def get_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """Get the hiring team for a job. Read-only.

    Users say "who's on the hiring team for Backend Engineer?" To find job_id:
    list_jobs → match by name. Returns members grouped by role:
    hiring_managers, recruiters, coordinators and sourcers. Each member has
    `id` (user ID), name, first_name, last_name, employee_id, `responsible`
    (recruiters/coordinators) and `assignment_id`.
    """
    team = await _team_rows(client, job_id)
    if client._is_error(team):
        return team
    user_ids = [r["user_id"] for rows in team.values() for r in rows if r.get("user_id")]
    users: dict[Any, dict[str, Any]] = {}
    if user_ids:
        found = await client.harvest_get_ids("/users", "ids", user_ids)
        if not client._is_error(found):
            users = {u.get("id"): u for u in found.get("items", [])}
    out: dict[str, Any] = {}
    for role, rows in team.items():
        members = []
        for row in rows:
            user = users.get(row.get("user_id"), {})
            member: dict[str, Any] = {
                "id": row.get("user_id"),
                "name": user.get("name"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "employee_id": user.get("employee_id"),
                "assignment_id": row.get("id"),
            }
            if "responsible" in row:
                member["responsible"] = row.get("responsible")
            members.append(member)
        out[role] = members
    return out


async def replace_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    hiring_managers: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {user_id: N} — replaces all hiring managers"),
    ] = None,
    sourcers: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {user_id: N} — replaces all sourcers"),
    ] = None,
    recruiters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {user_id: N, candidate_responsibility?: "
            "active|inactive|future|all} — replaces all recruiters"
        ),
    ] = None,
    coordinators: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {user_id: N, candidate_responsibility?: "
            "active|inactive|future|all} — replaces all coordinators"
        ),
    ] = None,
) -> dict[str, Any]:
    """Replace the hiring team for a job. Write operation — overwrites existing members.

    Only the roles you pass are replaced; omitted roles are left alone.
    Members missing from a passed list are removed and new ones are added.
    To find job_id: list_jobs → match by name. For member user_ids:
    list_users → match each person by name. Returns `added`, `removed` and
    any per-member `errors`.
    """
    desired = {
        "hiring_managers": hiring_managers,
        "recruiters": recruiters,
        "coordinators": coordinators,
        "sourcers": sourcers,
    }
    team = await _team_rows(client, job_id)
    if client._is_error(team):
        return team
    added: list[Any] = []
    removed: list[Any] = []
    errors: list[Any] = []
    for role, members in desired.items():
        if members is None:
            continue
        current = {row.get("user_id"): row for row in team[role]}
        wanted = {_member_user_id(m): m for m in members}
        for uid, row in current.items():
            if uid in wanted:
                continue
            res = await client.harvest_delete(f"{_endpoint(role)}/{row['id']}")
            if client._is_error(res):
                errors.append({"role": role, "user_id": uid, "action": "remove", "error": res})
            else:
                removed.append({"role": role, "user_id": uid})
        for uid, member in wanted.items():
            if uid in current:
                continue
            res = await client.harvest_post(
                _endpoint(role), json_data=_add_body(job_id, role, member)
            )
            if client._is_error(res):
                errors.append({"role": role, "user_id": uid, "action": "add", "error": res})
            else:
                added.append({"role": role, "user_id": uid, "assignment_id": res.get("id")})
    return _summary(added, removed, errors)


async def add_hiring_team_members(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    hiring_managers: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Array of {user_id: N} to add as hiring managers"),
    ] = None,
    sourcers: Annotated[
        list[dict[str, Any]] | None, Field(description="Array of {user_id: N} to add as sourcers")
    ] = None,
    recruiters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {user_id: N, candidate_responsibility?: "
            "active|inactive|future|all} to add as recruiters"
        ),
    ] = None,
    coordinators: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {user_id: N, candidate_responsibility?: "
            "active|inactive|future|all} to add as coordinators"
        ),
    ] = None,
) -> dict[str, Any]:
    """Add members to a hiring team without replacing existing ones. Write operation.

    To find job_id: list_jobs → match by name. For member user_ids: list_users
    → match by name. Returns `added` and any per-member `errors`.
    """
    requested = {
        "hiring_managers": hiring_managers,
        "recruiters": recruiters,
        "coordinators": coordinators,
        "sourcers": sourcers,
    }
    added: list[Any] = []
    errors: list[Any] = []
    for role, members in requested.items():
        for member in members or []:
            uid = _member_user_id(member)
            res = await client.harvest_post(
                _endpoint(role), json_data=_add_body(job_id, role, member)
            )
            if client._is_error(res):
                errors.append({"role": role, "user_id": uid, "action": "add", "error": res})
            else:
                added.append({"role": role, "user_id": uid, "assignment_id": res.get("id")})
    return _summary(added, [], errors)


async def remove_hiring_team_member(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    user_id: Annotated[
        int, Field(description="User ID to remove from the hiring team — get from get_hiring_team")
    ],
) -> dict[str, Any]:
    """Remove someone from a job's hiring team. Write operation.

    Removes the user from every hiring-team role they hold on the job. To
    find job_id: list_jobs → match by name. For user_id: list_users → match
    by name, or get_hiring_team to see current members and their IDs.
    """
    team = await _team_rows(client, job_id)
    if client._is_error(team):
        return team
    removed: list[Any] = []
    errors: list[Any] = []
    for role, rows in team.items():
        for row in rows:
            if row.get("user_id") != user_id:
                continue
            res = await client.harvest_delete(f"{_endpoint(role)}/{row['id']}")
            if client._is_error(res):
                errors.append({"role": role, "user_id": user_id, "action": "remove",
                               "error": res})
            else:
                removed.append({"role": role, "user_id": user_id})
    if not removed and not errors:
        return {"error": f"User {user_id} is not on the hiring team for job {job_id}.",
                "status_code": 404}
    return _summary([], removed, errors)


def _summary(added: list[Any], removed: list[Any], errors: list[Any]) -> dict[str, Any]:
    """Summarise per-member writes; when nothing succeeded, return an error dict."""
    if errors and not added and not removed:
        return {
            "error": "No hiring team changes were made.",
            "status_code": errors[0]["error"].get("status_code", 422),
            "detail": errors,
        }
    out: dict[str, Any] = {"added": added, "removed": removed}
    if errors:
        out["errors"] = errors
    return out

"""FastMCP server with tool registration and CLI entry point."""

from __future__ import annotations

import functools
import inspect
import os
import sys
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.permissions import UserPermissions, resolve_user_permissions

load_dotenv()

_client: GreenhouseClient | None = None
_user_permissions: UserPermissions | None = None


def _check_job_scope(
    perms: UserPermissions | None,
    job_id: int | None,
) -> None:
    """Raise PermissionError if the user is not permitted to write to this job."""
    if perms is None:
        return  # No user-scoped mode — skip check
    if job_id is None:
        return  # No job context to check
    if perms.permitted_job_ids is None:
        return  # Site admin — all jobs allowed
    if job_id in perms.permitted_job_ids:
        return
    raise PermissionError(
        f"User {perms.name} (ID {perms.user_id}) is not permitted "
        f"to write to job {job_id}. "
        f"They have access to jobs: {sorted(perms.permitted_job_ids)}"
    )


def get_client() -> GreenhouseClient:
    """Get or create the shared Greenhouse client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GREENHOUSE_API_KEY")
    board_token = os.environ.get("GREENHOUSE_BOARD_TOKEN")
    on_behalf_of = os.environ.get("GREENHOUSE_ON_BEHALF_OF")

    if not api_key and not board_token:
        raise ValueError(
            "At least one of GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN is required.\n"
            "Harvest API key: Configure > Dev Center > API Credential Management in Greenhouse.\n"
            "Board token: your public job board URL slug."
        )

    _client = GreenhouseClient(
        api_key=api_key,
        board_token=board_token,
        on_behalf_of=on_behalf_of,
    )
    return _client


def _make_tool_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Create a wrapper that injects get_client() and has the correct signature."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        client = get_client()
        return await fn(client, *args, **kwargs)

    # Remove the `client` parameter from the signature so FastMCP
    # doesn't expose it as a tool parameter.
    orig_sig = inspect.signature(fn)
    params = [p for p in orig_sig.parameters.values() if p.name != "client"]
    wrapper.__signature__ = orig_sig.replace(parameters=params)  # type: ignore[attr-defined]
    return wrapper


# ---------------------------------------------------------------------------
# Tool profiles
# ---------------------------------------------------------------------------

# Write tools allowed in recruiter mode — core pipeline management, not admin.
_RECRUITER_WRITE_TOOLS: set[str] = {
    # Pipeline management
    "reject_application",
    "unreject_application",
    "advance_application",
    "move_application",
    "move_application_same_job",
    "hire_application",
    "create_application",
    "update_application",
    "update_rejection_reason",
    # Bulk operations
    "bulk_reject",
    "bulk_advance",
    "bulk_tag",
    # Candidate interaction
    "add_note_to_candidate",
    "add_email_note_to_candidate",
    "add_tag_to_candidate",
    "remove_tag_from_candidate",
    "add_attachment",
    "add_attachment_to_application",
    "update_candidate",
    # Prospects
    "add_prospect",
    "convert_prospect",
    # Interviews
    "create_interview",
    "update_interview",
    "delete_interview",
}

# Webhook tools that are read-only (safe in any profile)
_WEBHOOK_READ_TOOLS: set[str] = {
    "webhook_list_rules",
    "webhook_get_rule",
    "webhook_list_events",
}

# Method names that indicate a write operation
_WRITE_METHODS: set[str] = {
    "harvest_post",
    "harvest_patch",
    "harvest_put",
    "harvest_delete",
    "ingestion_post",
    "board_post",
}


def _is_write_tool(fn: Callable[..., Any]) -> bool:
    """Check if a tool function calls any write client methods."""
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        return False
    return any(m in source for m in _WRITE_METHODS)


def _should_register(name: str, fn: Callable[..., Any], profile: str) -> bool:
    """Decide whether a tool should be registered based on the active profile."""
    if profile == "full":
        return True
    if profile == "read-only":
        return not _is_write_tool(fn)
    # recruiter: allow reads + approved write tools
    if _is_write_tool(fn):
        return name in _RECRUITER_WRITE_TOOLS
    return True


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all tools."""
    mcp = FastMCP("Greenhouse")
    mcp.description = "Comprehensive MCP server for the full Greenhouse API (~175 tools)"  # type: ignore[attr-defined]

    # --- Determine tool profile ---
    profile_raw = os.environ.get("GREENHOUSE_TOOL_PROFILE", "").lower().strip()
    read_only = os.environ.get("GREENHOUSE_READ_ONLY", "").lower() in (
        "true", "1", "yes",
    )
    user_id_raw = os.environ.get("GREENHOUSE_USER_ID", "").strip()

    if user_id_raw:
        import asyncio

        client = get_client()
        user_id = int(user_id_raw)

        try:
            perms = asyncio.run(
                resolve_user_permissions(client, user_id=user_id),
            )
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

        global _user_permissions
        _user_permissions = perms
        profile = perms.profile
        client.set_on_behalf_of(str(user_id))

        jobs_info = (
            f" | Jobs: {len(perms.permitted_job_ids)}"
            if perms.permitted_job_ids is not None
            else ""
        )
        print(
            f"User: {perms.name} ({perms.email}) | "
            f"Admin: {perms.site_admin} | "
            f"Derived profile: {profile}{jobs_info}",
            file=sys.stderr,
        )
    elif profile_raw in ("full", "recruiter", "read-only"):
        profile = profile_raw
    elif read_only:
        profile = "read-only"
    else:
        profile = "full"

    # --- Harvest tools ---
    from greenhouse_mcp.harvest import (
        activity_feed,
        analytics,
        applications,
        approvals,
        attachments,
        batch,
        candidates,
        close_reasons,
        custom_fields,
        demographics,
        departments,
        education,
        eeoc,
        email_templates,
        hiring_team,
        interviews,
        job_openings,
        job_posts,
        job_stages,
        jobs,
        offers,
        offices,
        prospect_pools,
        rejection_reasons,
        scorecards,
        screening,
        search,
        sources,
        sourcing,
        tags,
        tracking_links,
        user_permissions,
        user_roles,
        users,
        workflows,
    )

    harvest_modules = [
        candidates,
        applications,
        jobs,
        job_posts,
        job_stages,
        job_openings,
        offers,
        scorecards,
        interviews,
        users,
        user_permissions,
        departments,
        offices,
        custom_fields,
        sources,
        rejection_reasons,
        email_templates,
        tags,
        activity_feed,
        eeoc,
        demographics,
        approvals,
        hiring_team,
        prospect_pools,
        close_reasons,
        tracking_links,
        user_roles,
        education,
        workflows,
        analytics,
        batch,
        search,
        attachments,
        screening,
        sourcing,
    ]

    # --- Job Board tools ---
    from greenhouse_mcp.job_board import (
        applications as board_applications,
    )
    from greenhouse_mcp.job_board import (
        board,
    )
    from greenhouse_mcp.job_board import (
        departments as board_departments,
    )
    from greenhouse_mcp.job_board import (
        educations as board_educations,
    )
    from greenhouse_mcp.job_board import (
        jobs as board_jobs,
    )
    from greenhouse_mcp.job_board import (
        offices as board_offices,
    )
    from greenhouse_mcp.job_board import (
        prospects as board_prospects,
    )

    board_modules = [
        board,
        board_jobs,
        board_departments,
        board_offices,
        board_prospects,
        board_educations,
        board_applications,
    ]

    # --- Ingestion tools ---
    from greenhouse_mcp.ingestion import (
        candidates as ing_candidates,
    )
    from greenhouse_mcp.ingestion import (
        jobs as ing_jobs,
    )
    from greenhouse_mcp.ingestion import (
        prospects as ing_prospects,
    )
    from greenhouse_mcp.ingestion import (
        retrieve as ing_retrieve,
    )
    from greenhouse_mcp.ingestion import (
        tracking as ing_tracking,
    )
    from greenhouse_mcp.ingestion import (
        users as ing_users,
    )

    ingestion_modules = [
        ing_candidates,
        ing_jobs,
        ing_prospects,
        ing_retrieve,
        ing_tracking,
        ing_users,
    ]

    api_key = os.environ.get("GREENHOUSE_API_KEY")
    board_token = os.environ.get("GREENHOUSE_BOARD_TOKEN")

    # Always register all tool definitions so MCP clients can discover
    # available tools. Credentials are checked at invocation time.
    api_modules = harvest_modules + ingestion_modules + board_modules

    registered = 0
    for module in api_modules:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if fn.__module__ != module.__name__:
                continue
            if not _should_register(name, fn, profile):
                continue
            wrapper = _make_tool_wrapper(fn)
            mcp.tool(name=name, description=fn.__doc__ or name)(wrapper)
            registered += 1

    # --- Webhook tools ---
    from pathlib import Path

    from greenhouse_mcp.webhook_receiver.models import WebhookDB
    from greenhouse_mcp.webhook_tools import events, rules, setup, testing

    _webhook_db: WebhookDB | None = None

    def get_webhook_db() -> WebhookDB:
        nonlocal _webhook_db
        if _webhook_db is None:
            db_path = os.environ.get(
                "WEBHOOK_DB_PATH",
                str(Path.home() / ".open-greenhouse-mcp" / "webhooks.db"),
            )
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            _webhook_db = WebhookDB(db_path)
        return _webhook_db

    def _make_webhook_tool_wrapper(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Create a wrapper that injects get_webhook_db() and has the correct signature."""

        @functools.wraps(fn)
        async def wrapper(*args: Any, _fn: Callable[..., Any] = fn, **kwargs: Any) -> Any:
            db = get_webhook_db()
            return await _fn(db, *args, **kwargs)

        orig_sig = inspect.signature(fn)
        params = [p for p in orig_sig.parameters.values() if p.name != "db"]
        wrapper.__signature__ = orig_sig.replace(parameters=params)  # type: ignore[attr-defined]
        return wrapper

    webhook_modules = [rules, events, testing, setup]
    for module in webhook_modules:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or not name.startswith("webhook_"):
                continue
            if profile != "full" and name not in _WEBHOOK_READ_TOOLS:
                continue

            sig = inspect.signature(fn)
            params = list(sig.parameters.values())

            if params and params[0].name == "db":
                wrapper = _make_webhook_tool_wrapper(fn)
                mcp.tool(name=name, description=fn.__doc__ or name)(wrapper)
            else:
                # No db parameter (like webhook_list_events)
                mcp.tool(name=name, description=fn.__doc__ or name)(fn)
            registered += 1

    # --- Startup banner ---
    from importlib.metadata import version as pkg_version

    from greenhouse_mcp.logging import logger

    try:
        ver = pkg_version("open-greenhouse-mcp")
    except Exception:
        ver = "dev"

    apis = []
    if api_key:
        apis.append("harvest")
        apis.append("ingestion")
    if board_token:
        apis.append("job-board")
    if not apis:
        apis.append("none (tools registered, credentials needed at invocation)")
    write_modes = {"full": "enabled", "recruiter": "recruiter-safe", "read-only": "disabled"}
    writes = write_modes.get(profile, "disabled")

    api_str = ", ".join(apis)
    print(
        f"open-greenhouse-mcp v{ver}\n"
        f"Profile: {profile} | Tools: {registered} | Writes: {writes} | APIs: {api_str}",
        file=sys.stderr,
    )

    logger.info(
        "server_started",
        version=ver,
        profile=profile,
        tools_registered=registered,
        writes=writes,
        apis=api_str,
    )

    return mcp


# Global server instance
mcp = create_server()


def main() -> None:
    """CLI entry point."""
    mcp.run()

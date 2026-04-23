from __future__ import annotations

import pytest
from httpx import Response

from greenhouse_mcp.permissions import resolve_user_permissions


class TestResolveUserPermissions:
    @pytest.mark.asyncio
    async def test_site_admin_gets_full(self, client, mock_api):
        mock_api.get("https://harvest.greenhouse.io/v1/users/123").mock(
            return_value=Response(200, json={
                "id": 123,
                "name": "Admin User",
                "site_admin": True,
                "disabled": False,
                "primary_email_address": "admin@co.com",
            })
        )

        perms = await resolve_user_permissions(client, user_id=123)

        assert perms.profile == "full"
        assert perms.user_id == 123
        assert perms.site_admin is True
        assert perms.permitted_job_ids is None  # None means all jobs

    @pytest.mark.asyncio
    async def test_job_admin_gets_recruiter(self, client, mock_api):
        mock_api.get("https://harvest.greenhouse.io/v1/users/456").mock(
            return_value=Response(200, json={
                "id": 456,
                "name": "Recruiter User",
                "site_admin": False,
                "disabled": False,
                "primary_email_address": "recruiter@co.com",
            })
        )
        mock_api.get("https://harvest.greenhouse.io/v1/users/456/permissions/jobs").mock(
            return_value=Response(200, json=[
                {"id": 1001, "job_id": 5001, "user_role_id": 4009207},
                {"id": 1002, "job_id": 5002, "user_role_id": 4009207},
            ])
        )

        perms = await resolve_user_permissions(client, user_id=456)

        assert perms.profile == "recruiter"
        assert perms.site_admin is False
        assert perms.permitted_job_ids == {5001, 5002}

    @pytest.mark.asyncio
    async def test_no_permissions_gets_read_only(self, client, mock_api):
        mock_api.get("https://harvest.greenhouse.io/v1/users/789").mock(
            return_value=Response(200, json={
                "id": 789,
                "name": "Viewer User",
                "site_admin": False,
                "disabled": False,
                "primary_email_address": "viewer@co.com",
            })
        )
        mock_api.get("https://harvest.greenhouse.io/v1/users/789/permissions/jobs").mock(
            return_value=Response(200, json=[])
        )

        perms = await resolve_user_permissions(client, user_id=789)

        assert perms.profile == "read-only"
        assert perms.permitted_job_ids == set()

    @pytest.mark.asyncio
    async def test_disabled_user_raises(self, client, mock_api):
        mock_api.get("https://harvest.greenhouse.io/v1/users/999").mock(
            return_value=Response(200, json={
                "id": 999,
                "name": "Disabled User",
                "site_admin": True,
                "disabled": True,
                "primary_email_address": "disabled@co.com",
            })
        )

        with pytest.raises(ValueError, match="disabled"):
            await resolve_user_permissions(client, user_id=999)

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self, client, mock_api):
        mock_api.get("https://harvest.greenhouse.io/v1/users/0").mock(
            return_value=Response(404, json={"message": "Resource not found"})
        )

        with pytest.raises(ValueError, match="Cannot resolve user"):
            await resolve_user_permissions(client, user_id=000)

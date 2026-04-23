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

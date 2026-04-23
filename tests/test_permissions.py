import pytest
import respx
from httpx import Response

from greenhouse_mcp.client import GreenhouseClient
from greenhouse_mcp.permissions import resolve_user_permissions


@pytest.fixture
def client():
    return GreenhouseClient(api_key="test-key")


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock


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

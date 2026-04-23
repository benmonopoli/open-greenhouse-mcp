from __future__ import annotations

import pytest

from greenhouse_mcp.permissions import UserPermissions
from greenhouse_mcp.server import _check_job_scope


class TestCheckJobScope:
    def test_site_admin_allowed_any_job(self):
        perms = UserPermissions(
            user_id=1, name="Admin", email="a@co.com",
            site_admin=True, disabled=False,
            profile="full", permitted_job_ids=None,
        )
        # Should not raise
        _check_job_scope(perms, job_id=99999)

    def test_recruiter_allowed_permitted_job(self):
        perms = UserPermissions(
            user_id=2, name="Recruiter", email="r@co.com",
            site_admin=False, disabled=False,
            profile="recruiter", permitted_job_ids={5001, 5002},
        )
        _check_job_scope(perms, job_id=5001)

    def test_recruiter_blocked_unpermitted_job(self):
        perms = UserPermissions(
            user_id=2, name="Recruiter", email="r@co.com",
            site_admin=False, disabled=False,
            profile="recruiter", permitted_job_ids={5001, 5002},
        )
        with pytest.raises(PermissionError, match="not permitted"):
            _check_job_scope(perms, job_id=9999)

    def test_no_user_permissions_skips_check(self):
        # When no GREENHOUSE_USER_ID is set, perms is None — skip check
        _check_job_scope(None, job_id=99999)

    def test_no_job_id_skips_check(self):
        perms = UserPermissions(
            user_id=2, name="Recruiter", email="r@co.com",
            site_admin=False, disabled=False,
            profile="recruiter", permitted_job_ids={5001},
        )
        # No job_id to check — should not raise
        _check_job_scope(perms, job_id=None)

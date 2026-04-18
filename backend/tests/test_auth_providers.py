"""Tests for GET /auth/providers and OAuth state-cookie handling."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_providers_reports_dev_enabled(client: AsyncClient) -> None:
    """Conftest sets ENABLE_DEV_AUTH=true, so ``dev`` must be True. None of
    the OAuth providers should be enabled in a clean test env."""

    res = await client.get("/api/v1/auth/providers")
    assert res.status_code == 200
    body = res.json()
    assert body["dev"] is True
    # No OAuth env vars are set in tests.
    assert body["google"] is False
    assert body["github"] is False
    assert body["gitlab"] is False


@pytest.mark.asyncio
async def test_oauth_callback_with_bad_state_redirects_and_clears_cookie(
    client: AsyncClient,
) -> None:
    """Missing state cookie => redirect to the login page with an error
    param, and the oauth_state cookie should be explicitly cleared."""

    res = await client.get(
        "/api/v1/auth/github/callback",
        params={"code": "abc", "state": "notarealstate"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "error=oauth_state" in (res.headers.get("location") or "")
    # The state cookie is cleared (delete_cookie emits an expired Set-Cookie).
    set_cookie = res.headers.get("set-cookie", "")
    assert "oauth_state=" in set_cookie

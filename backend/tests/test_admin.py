"""Coverage for platform super-user admin surface + org-creation gating.

Tests exercise `/api/v1/admin/*` endpoints, the first-user auto-bootstrap,
the ban enforcement on login, and that organization creation is gated on
`can_create_orgs` or `is_superuser`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, username: str) -> dict:
    res = await client.post("/api/v1/auth/dev/login", json={"username": username})
    assert res.status_code == 204, res.text
    client.cookies.update(res.cookies)
    me = await client.get("/api/v1/users/me")
    assert me.status_code == 200
    return me.json()


async def _logout(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/logout")
    client.cookies.clear()


@pytest.mark.asyncio
async def test_first_user_becomes_superuser(client: AsyncClient) -> None:
    me = await _login(client, "root")
    assert me["is_superuser"] is True
    assert me["can_create_orgs"] is True


@pytest.mark.asyncio
async def test_second_user_is_regular(client: AsyncClient) -> None:
    first = await _login(client, "root")
    assert first["is_superuser"] is True
    await _logout(client)

    second = await _login(client, "alice")
    assert second["is_superuser"] is False
    assert second["can_create_orgs"] is False


@pytest.mark.asyncio
async def test_non_admin_cannot_see_admin_users_list(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    # 404 — admin surface is existence-hidden from non-super-users.
    res = await client.get("/api/v1/admin/users")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_admin_users_list_filters_by_query(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "bob")
    await _logout(client)
    await _login(client, "root")

    res = await client.get("/api/v1/admin/users?q=ali")
    assert res.status_code == 200
    usernames = {u["username"] for u in res.json()}
    assert usernames == {"alice"}


@pytest.mark.asyncio
async def test_superuser_cannot_self_demote(client: AsyncClient) -> None:
    await _login(client, "root")
    res = await client.patch(
        "/api/v1/admin/users/root/superuser",
        json={"is_superuser": False},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_promote_and_demote_user(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")

    up = await client.patch(
        "/api/v1/admin/users/alice/superuser", json={"is_superuser": True}
    )
    assert up.status_code == 200
    assert up.json()["is_superuser"] is True
    assert up.json()["can_create_orgs"] is True

    down = await client.patch(
        "/api/v1/admin/users/alice/superuser", json={"is_superuser": False}
    )
    assert down.status_code == 200
    assert down.json()["is_superuser"] is False


@pytest.mark.asyncio
async def test_toggle_can_create_orgs(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")

    denied = await client.post("/api/v1/orgs", json={"name": "Acme"})
    assert denied.status_code == 403

    await _logout(client)
    await _login(client, "root")
    grant = await client.patch(
        "/api/v1/admin/users/alice/can-create-orgs", json={"allowed": True}
    )
    assert grant.status_code == 200
    assert grant.json()["can_create_orgs"] is True

    await _logout(client)
    await _login(client, "alice")
    allowed = await client.post("/api/v1/orgs", json={"name": "Acme"})
    assert allowed.status_code == 201


@pytest.mark.asyncio
async def test_cannot_revoke_superuser_org_creation(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")
    await client.patch(
        "/api/v1/admin/users/alice/superuser", json={"is_superuser": True}
    )
    res = await client.patch(
        "/api/v1/admin/users/alice/can-create-orgs", json={"allowed": False}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_ban_blocks_login_and_returns_reason(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")

    res = await client.post(
        "/api/v1/admin/users/alice/ban",
        json={"reason": "Terms of service violation"},
    )
    assert res.status_code == 200
    assert res.json()["is_banned"] is True
    assert res.json()["ban_reason"] == "Terms of service violation"

    await _logout(client)
    banned = await client.post("/api/v1/auth/dev/login", json={"username": "alice"})
    assert banned.status_code == 403
    body = banned.json()
    assert body["detail"]["code"] == "banned"
    assert body["detail"]["reason"] == "Terms of service violation"


@pytest.mark.asyncio
async def test_ban_revokes_active_session(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    # Alice has an active session here; now root bans her.
    alice_cookies = dict(client.cookies)
    await _logout(client)
    await _login(client, "root")
    res = await client.post(
        "/api/v1/admin/users/alice/ban", json={"reason": "spam"}
    )
    assert res.status_code == 200

    # Restore Alice's prior cookies and check that protected endpoints reject.
    client.cookies.clear()
    client.cookies.update(alice_cookies)
    me = await client.get("/api/v1/users/me")
    # The ban both deletes Alice's Session row (401) and, if anything survived,
    # `get_current_user` would reject a banned user with 403. Either is correct.
    assert me.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cannot_ban_superuser(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")
    await client.patch(
        "/api/v1/admin/users/alice/superuser", json={"is_superuser": True}
    )
    res = await client.post(
        "/api/v1/admin/users/alice/ban", json={"reason": "test"}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_unban_restores_login(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")
    await client.post("/api/v1/admin/users/alice/ban", json={"reason": "x"})
    unban = await client.post("/api/v1/admin/users/alice/unban")
    assert unban.status_code == 200
    assert unban.json()["is_banned"] is False
    await _logout(client)
    res = await client.post("/api/v1/auth/dev/login", json={"username": "alice"})
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_transfer_org_ownership(client: AsyncClient, session_factory) -> None:
    from sqlalchemy import select

    from app.models.organization import Membership, Organization
    from app.models.user import User

    await _login(client, "root")
    # root creates a team org (root is super-user so can_create_orgs passes)
    created = await client.post("/api/v1/orgs", json={"name": "Team Z"})
    slug = created.json()["slug"]
    await _logout(client)
    await _login(client, "zoe")
    await _logout(client)
    await _login(client, "root")

    res = await client.post(
        f"/api/v1/admin/orgs/{slug}/transfer-owner",
        json={"new_owner_username": "zoe"},
    )
    assert res.status_code == 200

    async with session_factory() as db:
        zoe = (
            await db.execute(select(User).where(User.username == "zoe"))
        ).scalar_one()
        org = (
            await db.execute(select(Organization).where(Organization.slug == slug))
        ).scalar_one()
        rows = (
            await db.execute(select(Membership).where(Membership.org_id == org.id))
        ).scalars().all()
        by_role = {m.user_id: m.role for m in rows}
        assert by_role[zoe.id] == "owner"
        assert org.owner_user_id == zoe.id
        # previous owner (root) is demoted to editor, not removed
        assert any(role == "editor" for uid, role in by_role.items() if uid != zoe.id)


@pytest.mark.asyncio
async def test_transfer_rejects_personal_org(client: AsyncClient) -> None:
    await _login(client, "root")
    await _logout(client)
    await _login(client, "alice")
    await _logout(client)
    await _login(client, "root")
    res = await client.post(
        "/api/v1/admin/orgs/alice/transfer-owner",
        json={"new_owner_username": "root"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_org_creation_gated_when_not_superuser_or_allowed(
    client: AsyncClient,
) -> None:
    await _login(client, "root")  # first = super-user
    await _logout(client)
    await _login(client, "alice")  # regular
    denied = await client.post("/api/v1/orgs", json={"name": "Alice Co"})
    assert denied.status_code == 403

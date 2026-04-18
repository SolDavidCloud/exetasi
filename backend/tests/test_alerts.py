"""Coverage for the alert surface.

Exercises creation/listing/acknowledgement for both system-wide and
per-org alerts, plus the window logic that hides past/future rows from
the "active" endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


async def _bootstrap(client: AsyncClient, *usernames: str) -> None:
    for name in usernames:
        await _login(client, name)
        await _logout(client)


@pytest.mark.asyncio
async def test_only_superuser_can_post_system_announcement(
    client: AsyncClient,
) -> None:
    await _bootstrap(client, "root", "alice")
    await _login(client, "alice")
    res = await client.post(
        "/api/v1/announcements", json={"title": "Hi", "body": "Hello"}
    )
    # Admin surface is existence-hidden from non-super-users.
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_active_announcements_visible_to_all_users(
    client: AsyncClient,
) -> None:
    await _bootstrap(client, "root", "alice")
    await _login(client, "root")
    made = await client.post(
        "/api/v1/announcements",
        json={
            "title": "Scheduled downtime",
            "body": "Planned maintenance tonight.",
            "severity": "warning",
        },
    )
    assert made.status_code == 201
    await _logout(client)

    await _login(client, "alice")
    active = await client.get("/api/v1/announcements/active")
    assert active.status_code == 200
    items = active.json()
    assert len(items) == 1
    assert items[0]["title"] == "Scheduled downtime"
    assert items[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_announcement_window_hides_past_and_future(
    client: AsyncClient,
) -> None:
    await _login(client, "root")
    past = {
        "title": "Old",
        "body": "past",
        "starts_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        "ends_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
    }
    future = {
        "title": "New",
        "body": "future",
        "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "ends_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
    }
    current = {"title": "Now", "body": "now"}
    for payload in (past, future, current):
        res = await client.post("/api/v1/announcements", json=payload)
        assert res.status_code == 201

    active = await client.get("/api/v1/announcements/active")
    titles = [a["title"] for a in active.json()]
    assert titles == ["Now"]


@pytest.mark.asyncio
async def test_acknowledge_hides_from_user(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice")
    await _login(client, "root")
    created = await client.post(
        "/api/v1/announcements", json={"title": "Banner", "body": "hi"}
    )
    announcement_id = created.json()["id"]
    await _logout(client)

    await _login(client, "alice")
    first = await client.get("/api/v1/announcements/active")
    assert len(first.json()) == 1

    ack = await client.post(f"/api/v1/alerts/system/{announcement_id}/ack")
    assert ack.status_code == 204

    second = await client.get("/api/v1/announcements/active")
    assert second.json() == []


@pytest.mark.asyncio
async def test_ack_is_idempotent(client: AsyncClient) -> None:
    await _login(client, "root")
    created = await client.post(
        "/api/v1/announcements", json={"title": "Banner", "body": "hi"}
    )
    aid = created.json()["id"]

    r1 = await client.post(f"/api/v1/alerts/system/{aid}/ack")
    r2 = await client.post(f"/api/v1/alerts/system/{aid}/ack")
    assert r1.status_code == 204
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_acknowledge_scoped_per_user(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "root")
    created = await client.post(
        "/api/v1/announcements", json={"title": "B", "body": "x"}
    )
    aid = created.json()["id"]
    await _logout(client)

    await _login(client, "alice")
    await client.post(f"/api/v1/alerts/system/{aid}/ack")
    assert (await client.get("/api/v1/announcements/active")).json() == []
    await _logout(client)

    # Bob did not dismiss it; he must still see it.
    await _login(client, "bob")
    assert len((await client.get("/api/v1/announcements/active")).json()) == 1


@pytest.mark.asyncio
async def test_delete_announcement_removes_it_for_everyone(
    client: AsyncClient,
) -> None:
    await _bootstrap(client, "root", "alice")
    await _login(client, "root")
    created = await client.post(
        "/api/v1/announcements", json={"title": "Drop", "body": "x"}
    )
    aid = created.json()["id"]
    deleted = await client.delete(f"/api/v1/announcements/{aid}")
    assert deleted.status_code == 204
    await _logout(client)

    await _login(client, "alice")
    assert (await client.get("/api/v1/announcements/active")).json() == []


@pytest.mark.asyncio
async def test_org_alert_requires_owner_or_superuser(
    client: AsyncClient,
) -> None:
    await _login(client, "root")
    made = await client.post("/api/v1/orgs", json={"name": "Team"})
    slug = made.json()["slug"]
    await _logout(client)

    await _login(client, "alice")
    # Non-member of the team org.
    res = await client.post(
        f"/api/v1/orgs/{slug}/alerts",
        json={"title": "x", "body": "y"},
    )
    # 404 because the org existence is hidden from non-members (auth gate
    # in org loader); owner-only gate applies after membership check.
    assert res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_org_owner_creates_and_member_sees_active_alert(
    client: AsyncClient, session_factory
) -> None:
    from app.models.organization import Membership, Organization
    from app.models.user import User
    from sqlalchemy import select

    await _bootstrap(client, "root", "alice")
    await _login(client, "root")
    made = await client.post("/api/v1/orgs", json={"name": "Team"})
    slug = made.json()["slug"]

    # Add alice as a member (viewer) so she can see the active alert.
    async with session_factory() as db:
        alice = (
            await db.execute(select(User).where(User.username == "alice"))
        ).scalar_one()
        org = (
            await db.execute(select(Organization).where(Organization.slug == slug))
        ).scalar_one()
        db.add(Membership(user_id=alice.id, org_id=org.id, role="viewer"))
        await db.commit()

    created = await client.post(
        f"/api/v1/orgs/{slug}/alerts",
        json={"title": "Welcome", "body": "Hi team", "severity": "info"},
    )
    assert created.status_code == 201
    await _logout(client)

    await _login(client, "alice")
    active = await client.get(f"/api/v1/orgs/{slug}/alerts/active")
    assert active.status_code == 200
    titles = [a["title"] for a in active.json()]
    assert titles == ["Welcome"]

    # Dismissing it hides it on subsequent reads.
    alert_id = active.json()[0]["id"]
    ack = await client.post(f"/api/v1/alerts/org/{alert_id}/ack")
    assert ack.status_code == 204
    after = await client.get(f"/api/v1/orgs/{slug}/alerts/active")
    assert after.json() == []


@pytest.mark.asyncio
async def test_org_alert_cross_org_id_probe_404s(
    client: AsyncClient, session_factory
) -> None:
    """Deleting an alert belonging to a different org must 404 even for a
    super-user, so a stolen alert id can't be used to mass-wipe alerts."""

    await _login(client, "root")
    left = await client.post("/api/v1/orgs", json={"name": "Left"})
    right = await client.post("/api/v1/orgs", json={"name": "Right"})
    left_slug = left.json()["slug"]
    right_slug = right.json()["slug"]

    made = await client.post(
        f"/api/v1/orgs/{left_slug}/alerts",
        json={"title": "LEFT", "body": "x"},
    )
    alert_id = made.json()["id"]
    wrong = await client.delete(f"/api/v1/orgs/{right_slug}/alerts/{alert_id}")
    assert wrong.status_code == 404

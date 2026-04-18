"""Coverage for the user-to-user messaging surface.

Exercises direct messages, the two fan-out endpoints, anti-duplicate and
anti-enumeration behaviour, and inbox/sent hygiene.
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


async def _bootstrap(client: AsyncClient, *usernames: str) -> None:
    """Create users in order; first becomes super-user automatically."""

    for name in usernames:
        await _login(client, name)
        await _logout(client)


@pytest.mark.asyncio
async def test_send_and_receive_direct_message(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")

    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "hey"},
    )
    assert res.status_code == 201, res.text
    payload = res.json()
    assert payload["body"] == "hey"
    assert payload["recipient_username"] == "bob"
    assert payload["target_kind"] == "direct"

    await _logout(client)
    await _login(client, "bob")
    inbox = await client.get("/api/v1/messages")
    assert inbox.status_code == 200
    body = inbox.json()
    assert body["unread"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["body"] == "hey"


@pytest.mark.asyncio
async def test_cannot_message_self(client: AsyncClient) -> None:
    await _login(client, "root")
    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "root", "body": "hi me"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_unknown_recipient_is_404(client: AsyncClient) -> None:
    await _login(client, "root")
    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "ghost", "body": "hi"},
    )
    # Shape the response identically to banned or missing — any probing
    # looks the same from the outside so the endpoint cannot be used as a
    # username oracle.
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_banned_recipient_hidden_as_404(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice")
    await _login(client, "root")
    await client.post("/api/v1/admin/users/alice/ban", json={"reason": "spam"})
    await _logout(client)
    await _login(client, "root")  # send from super-user to the banned user
    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "alice", "body": "ping"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_message_collapsed(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")
    first = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "hello"},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "hello"},
    )
    assert second.status_code == 201
    # Both calls resolve to the same row thanks to the dedup window.
    assert first.json()["id"] == second.json()["id"]

    await _logout(client)
    await _login(client, "bob")
    inbox = await client.get("/api/v1/messages")
    assert inbox.json()["unread"] == 1


@pytest.mark.asyncio
async def test_length_enforced_on_send(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")
    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "x" * 501},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_fanout_to_superusers(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    # Promote bob so there are two super-users.
    await _login(client, "root")
    await client.patch("/api/v1/admin/users/bob/superuser", json={"is_superuser": True})
    await _logout(client)

    await _login(client, "alice")
    res = await client.post(
        "/api/v1/messages/to-superusers",
        json={"body": "help needed"},
    )
    assert res.status_code == 201
    assert res.json()["recipients"] == 2
    await _logout(client)

    for name in ("root", "bob"):
        await _login(client, name)
        inbox = await client.get("/api/v1/messages")
        items = inbox.json()["items"]
        assert any(
            m["target_kind"] == "superusers" and m["body"] == "help needed"
            for m in items
        )
        await _logout(client)


@pytest.mark.asyncio
async def test_fanout_to_org_owners_requires_membership(
    client: AsyncClient,
) -> None:
    await _login(client, "root")
    created = await client.post("/api/v1/orgs", json={"name": "Team Q"})
    slug = created.json()["slug"]
    await _logout(client)

    await _login(client, "alice")  # not a member of the org
    res = await client.post(
        f"/api/v1/messages/to-org/{slug}", json={"body": "hello team"}
    )
    # Non-members get a 404 — existence of the org is hidden to outsiders.
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_flow(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")
    sent = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "note"},
    )
    msg_id = sent.json()["id"]
    await _logout(client)

    await _login(client, "bob")
    assert (await client.get("/api/v1/messages")).json()["unread"] == 1
    res = await client.post(f"/api/v1/messages/{msg_id}/read")
    assert res.status_code == 200
    assert res.json()["read_at"] is not None
    assert (await client.get("/api/v1/messages")).json()["unread"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")
    await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "one"},
    )
    # Distinct body escapes the dedup window.
    await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "two"},
    )
    await _logout(client)

    await _login(client, "bob")
    assert (await client.get("/api/v1/messages")).json()["unread"] == 2
    res = await client.post("/api/v1/messages/read-all")
    assert res.status_code == 200
    assert res.json()["recipients"] == 2
    assert (await client.get("/api/v1/messages")).json()["unread"] == 0


@pytest.mark.asyncio
async def test_sent_excludes_other_users(client: AsyncClient) -> None:
    await _bootstrap(client, "root", "alice", "bob")
    await _login(client, "alice")
    await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "bob", "body": "a to b"},
    )
    sent = await client.get("/api/v1/messages/sent")
    assert sent.status_code == 200
    bodies = [m["body"] for m in sent.json()]
    assert bodies == ["a to b"]

    await _logout(client)
    await _login(client, "bob")
    sent_bob = await client.get("/api/v1/messages/sent")
    assert sent_bob.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_cannot_send(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/messages/to-user",
        json={"recipient_username": "whoever", "body": "hi"},
    )
    assert res.status_code == 401

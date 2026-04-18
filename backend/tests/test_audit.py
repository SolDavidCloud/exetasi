"""Tests for audit-log writes and the read endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_self_scope_captures_login_and_org_create(
    client: AsyncClient,
) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "auditor"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    created = await client.post("/api/v1/orgs", json={"name": "Audit Team"})
    assert created.status_code == 201

    log = await client.get("/api/v1/audit-log")
    assert log.status_code == 200
    actions = {entry["action"] for entry in log.json()["entries"]}
    assert "auth.login.dev" in actions
    assert "org.created" in actions


@pytest.mark.asyncio
async def test_audit_org_scope_requires_owner(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "owner2"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)
    created = await client.post("/api/v1/orgs", json={"name": "Owner Two"})
    slug = created.json()["slug"]

    # Owner sees org-scoped entries.
    ok = await client.get("/api/v1/audit-log", params={"org_slug": slug})
    assert ok.status_code == 200
    actions = {entry["action"] for entry in ok.json()["entries"]}
    assert "org.created" in actions

    # Non-member gets 404 (existence hiding).
    await client.post("/api/v1/auth/logout")
    client.cookies.clear()
    await client.post("/api/v1/auth/dev/login", json={"username": "stranger"})
    denied = await client.get("/api/v1/audit-log", params={"org_slug": slug})
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_username_change_audits_and_updates_personal_slug(
    client: AsyncClient,
) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "oldname"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    # Personal org is at /oldname.
    listed = await client.get("/api/v1/orgs")
    slugs_before = {o["slug"] for o in listed.json()}
    assert "oldname" in slugs_before

    # Change username.
    patched = await client.patch("/api/v1/users/me", json={"username": "newname"})
    assert patched.status_code == 200
    assert patched.json()["username"] == "newname"

    # Personal org slug should have resynced.
    listed2 = await client.get("/api/v1/orgs")
    slugs_after = {o["slug"] for o in listed2.json()}
    assert "newname" in slugs_after
    assert "oldname" not in slugs_after

    log = await client.get("/api/v1/audit-log")
    actions = {entry["action"] for entry in log.json()["entries"]}
    assert "user.updated" in actions

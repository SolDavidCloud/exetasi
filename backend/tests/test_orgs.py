import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_orgs_after_dev_login(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "bob"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    orgs = await client.get("/api/v1/orgs")
    assert orgs.status_code == 200
    data = orgs.json()
    assert len(data) == 1
    assert data[0]["is_personal"] is True
    assert data[0]["slug"] == "bob"
    assert data[0]["banner_url"] is None
    assert data[0]["primary_color"] is None
    assert data[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_get_single_org(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "carol"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    one = await client.get("/api/v1/orgs/carol")
    assert one.status_code == 200
    body = one.json()
    assert body["slug"] == "carol"
    assert body["role"] == "owner"


@pytest.mark.asyncio
async def test_owner_can_update_team_org_theme(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "dora"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    created = await client.post(
        "/api/v1/orgs",
        json={"name": "Acme Co", "description": "Quality quizzes"},
    )
    assert created.status_code == 201
    slug = created.json()["slug"]

    patched = await client.patch(
        f"/api/v1/orgs/{slug}",
        json={
            "description": "Updated",
            "primary_color": "#4F46E5",
            "secondary_color": "#0EA5A4",
            "accent_color": "#F59E0B",
            "banner_url": "https://example.com/banner.png",
            "avatar_url": "https://example.com/icon.png",
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["description"] == "Updated"
    assert body["primary_color"] == "#4f46e5"
    assert body["banner_url"] == "https://example.com/banner.png"


@pytest.mark.asyncio
async def test_patch_rejects_bad_color(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "eve"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    created = await client.post("/api/v1/orgs", json={"name": "Eve Team"})
    slug = created.json()["slug"]

    bad = await client.patch(
        f"/api/v1/orgs/{slug}",
        json={"primary_color": "not-a-color"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_personal_org_slug_cannot_be_changed(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "frank"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)

    bad = await client.patch("/api/v1/orgs/frank", json={"slug": "new-slug"})
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_non_owner_cannot_update(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "grace"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)
    created = await client.post("/api/v1/orgs", json={"name": "Grace Team"})
    slug = created.json()["slug"]
    # log out and sign in as someone else without membership
    await client.post("/api/v1/auth/logout")
    client.cookies.clear()
    res2 = await client.post("/api/v1/auth/dev/login", json={"username": "henry"})
    assert res2.status_code == 204
    client.cookies.update(res2.cookies)

    forbidden = await client.patch(f"/api/v1/orgs/{slug}", json={"name": "Hijack"})
    # The user isn't even a member, so the API reports 404 for the org to avoid leaking existence.
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_non_owner_member_gets_403_and_role_exposed(
    client: AsyncClient, session_factory
) -> None:
    """A member with a non-owner role sees role in responses and is
    forbidden (403) from PATCH — distinct from non-members (404)."""
    from sqlalchemy import select

    from app.models.organization import Membership, Organization
    from app.models.user import User

    res = await client.post("/api/v1/auth/dev/login", json={"username": "owner1"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)
    created = await client.post("/api/v1/orgs", json={"name": "Team One"})
    slug = created.json()["slug"]
    assert created.json()["role"] == "owner"

    await client.post("/api/v1/auth/logout")
    client.cookies.clear()
    res2 = await client.post("/api/v1/auth/dev/login", json={"username": "viewer1"})
    assert res2.status_code == 204
    client.cookies.update(res2.cookies)

    async with session_factory() as db:
        viewer = (
            await db.execute(select(User).where(User.username == "viewer1"))
        ).scalar_one()
        org = (
            await db.execute(select(Organization).where(Organization.slug == slug))
        ).scalar_one()
        db.add(Membership(user_id=viewer.id, org_id=org.id, role="viewer"))
        await db.commit()

    got = await client.get(f"/api/v1/orgs/{slug}")
    assert got.status_code == 200
    assert got.json()["role"] == "viewer"

    forbidden = await client.patch(f"/api/v1/orgs/{slug}", json={"name": "Hijack"})
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_patch_rejects_dangerous_url_schemes(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "mallory"})
    assert res.status_code == 204
    client.cookies.update(res.cookies)
    created = await client.post("/api/v1/orgs", json={"name": "Mallory Co"})
    slug = created.json()["slug"]

    for bad_url in (
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "not-a-url",
    ):
        resp = await client.patch(
            f"/api/v1/orgs/{slug}", json={"avatar_url": bad_url}
        )
        assert resp.status_code == 422, f"expected 422 for {bad_url!r}"
        resp2 = await client.patch(
            f"/api/v1/orgs/{slug}", json={"banner_url": bad_url}
        )
        assert resp2.status_code == 422, f"expected 422 for {bad_url!r}"

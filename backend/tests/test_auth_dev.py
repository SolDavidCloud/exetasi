import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dev_login_sets_session_cookie(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "alice"})
    assert res.status_code == 204
    assert "exetasi_session" in res.cookies
    client.cookies.update(res.cookies)

    me = await client.get("/api/v1/users/me")
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "alice"

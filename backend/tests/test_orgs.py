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

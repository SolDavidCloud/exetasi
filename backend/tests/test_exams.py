import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_exam_for_org(client: AsyncClient) -> None:
    res = await client.post("/api/v1/auth/dev/login", json={"username": "carol"})
    client.cookies.update(res.cookies)

    exams = await client.get("/api/v1/orgs/carol/exams")
    assert exams.status_code == 200
    assert exams.json() == []

    created = await client.post(
        "/api/v1/orgs/carol/exams",
        json={"name": "Sample exam", "public_description": "Hello", "private_description": ""},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Sample exam"

    listed = await client.get("/api/v1/orgs/carol/exams")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

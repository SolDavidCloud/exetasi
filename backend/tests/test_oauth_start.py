import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_github_start_returns_503_when_unconfigured(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/github/start", follow_redirects=False)
    assert res.status_code == 503
    assert "GITHUB_CLIENT_ID" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_google_start_returns_503_when_unconfigured(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/google/start", follow_redirects=False)
    assert res.status_code == 503
    assert "GOOGLE_CLIENT_ID" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_gitlab_start_returns_503_when_unconfigured(client: AsyncClient) -> None:
    res = await client.get("/api/v1/auth/gitlab/start", follow_redirects=False)
    assert res.status_code == 503
    assert "GITLAB_CLIENT_ID" in res.json().get("detail", "")

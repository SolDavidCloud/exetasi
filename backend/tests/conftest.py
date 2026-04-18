from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENABLE_DEV_AUTH", "true")

from app.core.ratelimit import limiter
from app.db.session import get_db
from app.main import app
from app.models import Base

# Disable per-IP rate limiting during tests — every request shares
# ``127.0.0.1`` so realistic limits would cause cascading 429s. Coverage for
# the limiter itself is better added as a dedicated integration test.
limiter.enabled = False


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    """Expose the same sessionmaker the FastAPI app uses during tests so
    individual tests can stitch together state (e.g. memberships) directly."""

    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def client(session_factory):
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

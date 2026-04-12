from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_session_token, new_session_token
from app.models.user import Session as DbSession
from app.models.user import User

_INACTIVITY = timedelta(days=7)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def create_session(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, DbSession]:
    token = new_session_token()
    now = datetime.now(UTC)
    row = DbSession(
        user_id=user_id,
        token_hash=hash_session_token(token),
        last_active_at=now,
        expires_at=now + _INACTIVITY,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return token, row


async def revoke_session(db: AsyncSession, token_hash: str) -> None:
    await db.execute(delete(DbSession).where(DbSession.token_hash == token_hash))
    await db.commit()


async def get_valid_session(db: AsyncSession, token: str) -> DbSession | None:
    token_hash = hash_session_token(token)
    result = await db.execute(select(DbSession).where(DbSession.token_hash == token_hash))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    now = datetime.now(UTC)
    if _as_utc(row.expires_at) < now:
        await revoke_session(db, token_hash)
        return None
    row.touch()
    await db.commit()
    await db.refresh(row)
    return row


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
    return result.scalar_one_or_none()

"""Platform-admin (super-user) privileged mutations.

All functions in this module assume the caller has already been authorised
as a super-user (use `app.api.deps.get_current_superuser`). The service
layer still re-checks safety invariants that cannot be expressed in a
route-layer dependency — e.g. "a super-user cannot demote themselves" and
"an organization must keep at least one owner".

Each function flushes audit rows but defers `commit()` to the caller so
audit trails stay in the same transaction as the mutation.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Membership, Organization
from app.models.user import Session as DbSession
from app.models.user import User
from app.services import audit_service


async def list_users(
    db: AsyncSession,
    *,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    """Return non-soft-deleted users matching an optional substring query.

    The admin panel is the only code path that needs to see banned users,
    so we deliberately include them here (unlike `get_user_by_id`).
    """

    stmt = select(User).where(User.is_deleted.is_(False)).order_by(User.username)
    if query:
        stmt = stmt.where(User.username.ilike(f"%{query.strip()}%"))
    stmt = stmt.limit(max(1, min(500, limit))).offset(max(0, offset))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_superuser(
    db: AsyncSession,
    *,
    actor: User,
    target_username: str,
    is_superuser: bool,
    ip: str | None,
) -> User:
    target = await _load_user(db, target_username)
    if target.id == actor.id and not is_superuser:
        # Self-demotion would strand the platform with no super-user and is
        # explicitly disallowed per product requirements.
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own super-user role.",
        )
    if target.is_superuser == is_superuser:
        return target
    target.is_superuser = is_superuser
    if is_superuser:
        # Promoted users keep their existing `can_create_orgs` flag but we
        # also grant it here so the UI doesn't have to special-case super-users
        # that were never allowed to create orgs before.
        target.can_create_orgs = True
    await audit_service.record(
        db,
        action="admin.user.role.set",
        actor_user_id=actor.id,
        target_type="user",
        target_id=target.id,
        metadata={"is_superuser": is_superuser, "username": target.username},
        ip=ip,
    )
    return target


async def set_can_create_orgs(
    db: AsyncSession,
    *,
    actor: User,
    target_username: str,
    allowed: bool,
    ip: str | None,
) -> User:
    target = await _load_user(db, target_username)
    if target.is_superuser and not allowed:
        # A super-user's org-creation permission is coupled to the role so we
        # don't end up with a super-user who mysteriously cannot create orgs.
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Super-users always have org creation rights.",
        )
    if target.can_create_orgs == allowed:
        return target
    target.can_create_orgs = allowed
    await audit_service.record(
        db,
        action="admin.user.can_create_orgs.set",
        actor_user_id=actor.id,
        target_type="user",
        target_id=target.id,
        metadata={"allowed": allowed, "username": target.username},
        ip=ip,
    )
    return target


async def ban_user(
    db: AsyncSession,
    *,
    actor: User,
    target_username: str,
    reason: str,
    ip: str | None,
) -> User:
    target = await _load_user(db, target_username)
    if target.id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="You cannot ban yourself."
        )
    if target.is_superuser:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Demote the user before banning them.",
        )
    target.is_banned = True
    target.ban_reason = reason.strip()[:500] if reason else None
    # Revoke all active sessions immediately so the ban takes effect without
    # waiting for cookie expiry.
    await db.execute(delete(DbSession).where(DbSession.user_id == target.id))
    await audit_service.record(
        db,
        action="admin.user.banned",
        actor_user_id=actor.id,
        target_type="user",
        target_id=target.id,
        metadata={"username": target.username, "reason": target.ban_reason},
        ip=ip,
    )
    return target


async def unban_user(
    db: AsyncSession,
    *,
    actor: User,
    target_username: str,
    ip: str | None,
) -> User:
    target = await _load_user(db, target_username)
    if not target.is_banned:
        return target
    target.is_banned = False
    target.ban_reason = None
    await audit_service.record(
        db,
        action="admin.user.unbanned",
        actor_user_id=actor.id,
        target_type="user",
        target_id=target.id,
        metadata={"username": target.username},
        ip=ip,
    )
    return target


async def transfer_org_ownership(
    db: AsyncSession,
    *,
    actor: User,
    org_slug: str,
    new_owner_username: str,
    ip: str | None,
) -> Organization:
    """Move the `owner` role to another user; previous owner keeps a
    membership (demoted to `editor`) so they don't lose access unless the
    super-user later removes them."""

    org = await _load_org(db, org_slug)
    if org.is_personal:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Personal organizations cannot change owners.",
        )
    new_owner = await _load_user(db, new_owner_username)
    if new_owner.is_banned or new_owner.is_deleted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Target user is not available."
        )

    membership_rows = await db.execute(
        select(Membership).where(Membership.org_id == org.id)
    )
    memberships = list(membership_rows.scalars().all())

    previous_owner_ids = [m.user_id for m in memberships if m.role == "owner"]

    new_owner_membership: Membership | None = None
    for m in memberships:
        if m.user_id == new_owner.id:
            new_owner_membership = m
            break

    if new_owner_membership is None:
        db.add(Membership(user_id=new_owner.id, org_id=org.id, role="owner"))
    else:
        new_owner_membership.role = "owner"

    # Demote prior owners to editor so we never have an org without at least
    # one owner mid-transaction (the new owner's membership was upserted above).
    for m in memberships:
        if m.user_id in previous_owner_ids and m.user_id != new_owner.id:
            m.role = "editor"

    org.owner_user_id = new_owner.id

    await audit_service.record(
        db,
        action="admin.org.owner.transferred",
        actor_user_id=actor.id,
        org_id=org.id,
        target_type="organization",
        target_id=org.id,
        metadata={
            "slug": org.slug,
            "new_owner": new_owner.username,
            "previous_owners": [str(uid) for uid in previous_owner_ids],
        },
        ip=ip,
    )
    return org


async def count_superusers(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(
            User.is_superuser.is_(True),
            User.is_deleted.is_(False),
            User.is_banned.is_(False),
        )
    )
    return int(result.scalar_one() or 0)


async def _load_user(db: AsyncSession, username: str) -> User:
    result = await db.execute(
        select(User).where(User.username == username, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _load_org(db: AsyncSession, slug: str) -> Organization:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


__all__ = [
    "ban_user",
    "count_superusers",
    "list_users",
    "set_can_create_orgs",
    "set_superuser",
    "transfer_org_ownership",
    "unban_user",
]

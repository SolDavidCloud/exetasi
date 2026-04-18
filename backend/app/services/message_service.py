"""User-to-user messaging.

The feature spec is deliberately minimal — flat message rows, no threads,
no attachments. The complexity here is:

1. **Fan-out**: sending "to org owners" or "to super-users" materialises
   one row per recipient so inbox queries stay O(inbox) without JOINs.
2. **Enumeration defence**: an exact-username lookup that misses must look
   the same to the client as one that hits, modulo a rate-limit penalty,
   so the messaging UI cannot be turned into a username oracle.
3. **Anti-duplicate guard**: the same body from the same sender to the
   same recipient within a short window collapses to one row, which makes
   it cheaper to retry and harder to mass-flood.

Like the rest of the service layer, callers are responsible for the final
``commit()``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Final

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.organization import Membership, Organization
from app.models.user import User

# Maximum spacing between two identical messages for the second to be
# dropped as a "retry / double-click" duplicate. Long enough to soak up
# jittery network retries, short enough that an intentional follow-up
# message is preserved.
_DEDUP_WINDOW: Final = timedelta(seconds=30)


class UnknownRecipientError(Exception):
    """Raised when a direct-message recipient cannot be found.

    Routes translate this into a 404 only *after* the rate-limiter has
    recorded a hit, so repeated misses cost the attacker more than hits.
    """


async def send_to_user(
    db: AsyncSession,
    *,
    sender: User,
    recipient_username: str,
    body: str,
) -> Message:
    if recipient_username.strip().lower() == sender.username.lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You cannot send a message to yourself.",
        )

    result = await db.execute(
        select(User).where(
            func.lower(User.username) == recipient_username.strip().lower(),
            User.is_deleted.is_(False),
        )
    )
    recipient = result.scalar_one_or_none()
    # Banned users stay reachable in the inbox surface so moderators can
    # still see context, but are hidden from the public send surface.
    if recipient is None or recipient.is_banned:
        raise UnknownRecipientError(recipient_username)

    existing = await _find_recent_duplicate(
        db,
        sender_id=sender.id,
        recipient_id=recipient.id,
        target_kind="direct",
        body=body,
    )
    if existing is not None:
        return existing

    row = Message(
        sender_id=sender.id,
        recipient_id=recipient.id,
        target_kind="direct",
        body=body,
    )
    db.add(row)
    await db.flush()
    return row


async def send_to_org_owners(
    db: AsyncSession,
    *,
    sender: User,
    org_slug: str,
    body: str,
) -> int:
    """Fan-out to every owner of the target org.

    Sender must themselves be a member (or super-user) so this isn't
    misused to spam org owners with unsolicited mail — we don't maintain
    a public list of owners.
    """

    org_res = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = org_res.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if not sender.is_superuser:
        mem_res = await db.execute(
            select(Membership).where(
                Membership.org_id == org.id, Membership.user_id == sender.id
            )
        )
        if mem_res.scalar_one_or_none() is None:
            # Hide existence of non-public orgs from non-members.
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

    owner_rows = await db.execute(
        select(Membership.user_id, User.is_banned, User.is_deleted)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.org_id == org.id,
            Membership.role == "owner",
            User.is_deleted.is_(False),
            User.is_banned.is_(False),
        )
    )
    owner_ids = [row[0] for row in owner_rows.all() if row[0] != sender.id]
    # Always drop the sender from the fan-out list even if they are an
    # owner themselves — it would be confusing to see your own "to owners"
    # message appear in your inbox.
    return await _fanout(
        db,
        sender=sender,
        recipient_ids=owner_ids,
        target_kind="org_owners",
        target_org_id=org.id,
        body=body,
    )


async def send_to_superusers(
    db: AsyncSession,
    *,
    sender: User,
    body: str,
) -> int:
    result = await db.execute(
        select(User.id).where(
            User.is_superuser.is_(True),
            User.is_banned.is_(False),
            User.is_deleted.is_(False),
        )
    )
    ids = [row[0] for row in result.all() if row[0] != sender.id]
    return await _fanout(
        db,
        sender=sender,
        recipient_ids=ids,
        target_kind="superusers",
        target_org_id=None,
        body=body,
    )


async def list_inbox(
    db: AsyncSession,
    *,
    user: User,
    limit: int = 100,
    offset: int = 0,
    unread_only: bool = False,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.recipient_id == user.id)
        .order_by(Message.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Message.read_at.is_(None))
    stmt = stmt.limit(max(1, min(500, limit))).offset(max(0, offset))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_sent(
    db: AsyncSession,
    *,
    user: User,
    limit: int = 100,
    offset: int = 0,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.sender_id == user.id)
        .order_by(Message.created_at.desc())
        .limit(max(1, min(500, limit)))
        .offset(max(0, offset))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_unread(db: AsyncSession, *, user: User) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(Message.recipient_id == user.id, Message.read_at.is_(None))
    )
    return int(result.scalar_one() or 0)


async def mark_read(
    db: AsyncSession,
    *,
    user: User,
    message_id: uuid.UUID,
) -> Message:
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.recipient_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found")
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
    return row


async def mark_all_read(db: AsyncSession, *, user: User) -> int:
    now = datetime.now(UTC)
    result = await db.execute(
        update(Message)
        .where(Message.recipient_id == user.id, Message.read_at.is_(None))
        .values(read_at=now)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0


async def hydrate_messages(
    db: AsyncSession, rows: list[Message]
) -> list[dict[str, object]]:
    """Attach sender/recipient usernames and org slug for API responses.

    The messages table only stores IDs so inbox queries stay narrow; this
    helper is the single place that widens them back out to the shape the
    clients expect.
    """

    if not rows:
        return []

    user_ids: set[uuid.UUID] = set()
    org_ids: set[uuid.UUID] = set()
    for r in rows:
        if r.sender_id:
            user_ids.add(r.sender_id)
        user_ids.add(r.recipient_id)
        if r.target_org_id:
            org_ids.add(r.target_org_id)

    user_rows = await db.execute(
        select(User.id, User.username).where(User.id.in_(user_ids))
    )
    username_by_id = {row[0]: row[1] for row in user_rows.all()}

    org_slug_by_id: dict[uuid.UUID, str] = {}
    if org_ids:
        org_rows = await db.execute(
            select(Organization.id, Organization.slug).where(
                Organization.id.in_(org_ids)
            )
        )
        org_slug_by_id = {row[0]: row[1] for row in org_rows.all()}

    payload: list[dict[str, object]] = []
    for r in rows:
        payload.append(
            {
                "id": r.id,
                "sender_id": r.sender_id,
                "sender_username": username_by_id.get(r.sender_id)
                if r.sender_id
                else None,
                "recipient_id": r.recipient_id,
                "recipient_username": username_by_id.get(r.recipient_id),
                "target_kind": r.target_kind,
                "target_org_id": r.target_org_id,
                "target_org_slug": org_slug_by_id.get(r.target_org_id)
                if r.target_org_id
                else None,
                "body": r.body,
                "created_at": r.created_at,
                "read_at": r.read_at,
            }
        )
    return payload


async def _fanout(
    db: AsyncSession,
    *,
    sender: User,
    recipient_ids: list[uuid.UUID],
    target_kind: str,
    target_org_id: uuid.UUID | None,
    body: str,
) -> int:
    if not recipient_ids:
        return 0

    # Deduplicate against recent rows in a single query so fan-out retries
    # don't blow up the inbox with duplicate copies.
    cutoff = datetime.now(UTC) - _DEDUP_WINDOW
    already = await db.execute(
        select(Message.recipient_id).where(
            Message.sender_id == sender.id,
            Message.recipient_id.in_(recipient_ids),
            Message.target_kind == target_kind,
            Message.body == body,
            Message.created_at >= cutoff,
            _nullable_eq(Message.target_org_id, target_org_id),
        )
    )
    skip = {row[0] for row in already.all()}
    fresh = [rid for rid in recipient_ids if rid not in skip]
    for rid in fresh:
        db.add(
            Message(
                sender_id=sender.id,
                recipient_id=rid,
                target_kind=target_kind,
                target_org_id=target_org_id,
                body=body,
            )
        )
    if fresh:
        await db.flush()
    return len(fresh)


async def _find_recent_duplicate(
    db: AsyncSession,
    *,
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    target_kind: str,
    body: str,
) -> Message | None:
    cutoff = datetime.now(UTC) - _DEDUP_WINDOW
    result = await db.execute(
        select(Message)
        .where(
            Message.sender_id == sender_id,
            Message.recipient_id == recipient_id,
            Message.target_kind == target_kind,
            Message.body == body,
            Message.created_at >= cutoff,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _nullable_eq(column, value):  # type: ignore[no-untyped-def]
    """``col = value`` that works when ``value`` is ``None``.

    SQL's ``NULL = NULL`` is false, so we have to spell out the compound
    condition when the value can be null (as it is for non-org targets).
    """

    if value is None:
        return column.is_(None)
    return and_(column.is_not(None), column == value)


__all__ = [
    "UnknownRecipientError",
    "count_unread",
    "hydrate_messages",
    "list_inbox",
    "list_sent",
    "mark_all_read",
    "mark_read",
    "send_to_org_owners",
    "send_to_superusers",
    "send_to_user",
]

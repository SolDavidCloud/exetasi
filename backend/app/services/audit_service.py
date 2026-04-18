"""Thin wrapper around the ``audit_logs`` table.

The service only buffers rows into the caller's ``AsyncSession`` — the
caller is responsible for committing. That lets the audit entry participate
in the same transaction as the action it describes, so we never end up with
"ghost" log rows for changes that got rolled back.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    metadata: Mapping[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    row = AuditLog(
        action=action[:64],
        actor_user_id=actor_user_id,
        org_id=org_id,
        target_type=(target_type[:32] if target_type else None),
        target_id=target_id,
        metadata_json=_serialize_metadata(metadata),
        ip=(ip[:64] if ip else None),
    )
    db.add(row)
    # Flush so the caller sees the id if they need it, but leave the commit
    # to the caller so we stay inside the same transaction.
    await db.flush()
    return row


def _serialize_metadata(metadata: Mapping[str, Any] | None) -> str:
    if not metadata:
        return "{}"
    try:
        # ``default=str`` makes dates/UUIDs serialisable without the caller
        # having to remember to coerce them.
        return json.dumps(dict(metadata), default=str, ensure_ascii=False)[:4096]
    except (TypeError, ValueError):
        return "{}"

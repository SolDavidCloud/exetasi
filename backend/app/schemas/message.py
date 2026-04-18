from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MessageTargetKind = Literal["direct", "org_owners", "superusers"]

# 500 chars is enforced at the schema layer per the feature spec; the DB
# column is TEXT to keep multibyte payloads intact.
_MAX_BODY = 500


def _validate_body(value: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError("body must not be empty")
    # We count Python characters (Unicode code points), not bytes, so emoji
    # don't eat into the budget at a variable rate.
    if len(v) > _MAX_BODY:
        raise ValueError(f"body must be <= {_MAX_BODY} characters")
    return v


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID | None
    sender_username: str | None = None
    recipient_id: uuid.UUID
    recipient_username: str | None = None
    target_kind: MessageTargetKind
    target_org_id: uuid.UUID | None = None
    target_org_slug: str | None = None
    body: str
    created_at: datetime
    read_at: datetime | None = None


class MessageInbox(BaseModel):
    items: list[MessagePublic]
    unread: int


class SendToUserRequest(BaseModel):
    recipient_username: str = Field(min_length=3, max_length=64)
    body: str = Field(min_length=1, max_length=_MAX_BODY)

    @field_validator("body")
    @classmethod
    def _check_body(cls, value: str) -> str:
        return _validate_body(value)


class SendToOrgOwnersRequest(BaseModel):
    body: str = Field(min_length=1, max_length=_MAX_BODY)

    @field_validator("body")
    @classmethod
    def _check_body(cls, value: str) -> str:
        return _validate_body(value)


class SendToSuperusersRequest(BaseModel):
    body: str = Field(min_length=1, max_length=_MAX_BODY)

    @field_validator("body")
    @classmethod
    def _check_body(cls, value: str) -> str:
        return _validate_body(value)


class SendResult(BaseModel):
    """Response for fan-out sends — tells the caller how many recipients
    got the message without leaking the individual user IDs."""

    recipients: int

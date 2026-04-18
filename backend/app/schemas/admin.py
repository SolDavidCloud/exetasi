from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AdminUserPublic(BaseModel):
    """Admin panel user row. Includes moderation state intentionally — this
    schema must NEVER be reused by non-admin endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    bio: str
    avatar_url: str | None = None
    is_superuser: bool
    is_banned: bool
    ban_reason: str | None = None
    can_create_orgs: bool


class SetSuperuserRequest(BaseModel):
    is_superuser: bool


class SetCanCreateOrgsRequest(BaseModel):
    allowed: bool


class BanUserRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class TransferOwnerRequest(BaseModel):
    new_owner_username: str = Field(min_length=3, max_length=64)

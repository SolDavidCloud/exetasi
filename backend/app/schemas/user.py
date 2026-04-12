from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    bio: str
    avatar_url: str | None = None


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    bio: str | None = Field(default=None, max_length=512)
    avatar_url: str | None = Field(default=None, max_length=2048)

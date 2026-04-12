from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    avatar_url: str | None = None
    is_personal: bool


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=96)
    description: str = Field(default="", max_length=2000)

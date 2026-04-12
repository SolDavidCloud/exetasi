from __future__ import annotations

import uuid

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExamPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    is_archived: bool
    visibility: str


class ExamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    public_description: str = Field(default="", max_length=50_000)
    private_description: str = Field(default="", max_length=50_000)
    visibility: Literal["public", "restricted"] = "public"

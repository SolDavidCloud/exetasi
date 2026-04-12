from __future__ import annotations

from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)

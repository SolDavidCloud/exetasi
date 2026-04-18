from __future__ import annotations

import re
import uuid
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ALLOWED_URL_SCHEMES = {"http", "https"}
MembershipRole = Literal["owner", "editor", "grader", "viewer"]


def _normalize_color(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    if not HEX_COLOR_RE.match(v):
        raise ValueError("color must be a hex string like #4F46E5 or #fff")
    return v.lower()


def _normalize_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    parsed = urlparse(v)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValueError("URL must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return v


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    avatar_url: str | None = None
    banner_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    is_personal: bool
    role: MembershipRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=96)
    description: str = Field(default="", max_length=2000)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=96)
    description: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=2048)
    banner_url: str | None = Field(default=None, max_length=2048)
    primary_color: str | None = Field(default=None, max_length=16)
    secondary_color: str | None = Field(default=None, max_length=16)
    accent_color: str | None = Field(default=None, max_length=16)

    @field_validator("primary_color", "secondary_color", "accent_color")
    @classmethod
    def _validate_colors(cls, value: str | None) -> str | None:
        return _normalize_color(value)

    @field_validator("avatar_url", "banner_url")
    @classmethod
    def _validate_urls(cls, value: str | None) -> str | None:
        return _normalize_http_url(value)

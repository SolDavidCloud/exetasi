from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.organization import _normalize_http_url

# Username character policy: conservative subset used consistently on both
# the backend and for personal-org slugs (see `utils/slug.py`).
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{2,63}$")


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    bio: str
    avatar_url: str | None = None
    is_superuser: bool = False
    can_create_orgs: bool = False


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    bio: str | None = Field(default=None, max_length=512)
    avatar_url: str | None = Field(default=None, max_length=2048)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _USERNAME_RE.match(value):
            raise ValueError(
                "Username must start with a letter or digit and contain only "
                "letters, digits, dots, dashes, or underscores."
            )
        return value

    @field_validator("avatar_url")
    @classmethod
    def _validate_avatar_url(cls, value: str | None) -> str | None:
        return _normalize_http_url(value)

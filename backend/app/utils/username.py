"""Helpers for normalising externally-sourced usernames.

OAuth providers return arbitrary strings for the user's handle. We never
want to persist those raw — they may contain whitespace, punctuation,
control chars, or characters that would break our personal-org slug
derivation (`utils/slug.py`). Keep this aligned with the regex enforced
by ``app.schemas.user.UserUpdate``.
"""

from __future__ import annotations

import re

_ALLOWED = re.compile(r"[^a-zA-Z0-9._-]")
_LEADING_NONALNUM = re.compile(r"^[^a-zA-Z0-9]+")


def sanitize_oauth_username(value: str, *, fallback: str, max_length: int = 64) -> str:
    """Produce a safe, schema-compliant username from an OAuth provider string.

    - Strips characters outside ``[a-zA-Z0-9._-]``.
    - Ensures the first character is alphanumeric.
    - Truncates to ``max_length``.
    - If the cleaned string would be shorter than 3 chars (the DB/schema
      minimum), falls back to ``fallback`` (already expected to be safe,
      e.g. ``github_<id>``).
    """

    cleaned = _ALLOWED.sub("", value or "")
    cleaned = _LEADING_NONALNUM.sub("", cleaned)
    cleaned = cleaned[:max_length]
    if len(cleaned) < 3:
        fb = _ALLOWED.sub("", fallback or "")
        fb = _LEADING_NONALNUM.sub("", fb)
        return fb[:max_length] or "user"
    return cleaned

from __future__ import annotations

import re


def slugify(value: str, *, max_length: int = 96) -> str:
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if len(s) == 0:
        s = "user"
    return s[:max_length]

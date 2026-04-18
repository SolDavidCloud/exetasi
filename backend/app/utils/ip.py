"""Best-effort client-IP extraction.

We only trust ``X-Forwarded-For`` when the backend is explicitly told it is
behind a reverse proxy (``TRUSTED_PROXY=true``). Otherwise an attacker
could spoof the audit log by sending the header directly.
"""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str | None:
    settings = get_settings()
    if settings.trusted_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Take the first (left-most) entry — that's the original client
            # per the proxy's appending convention.
            first = xff.split(",", 1)[0].strip()
            if first:
                return first[:64]
    client = request.client
    if client is None:
        return None
    return (client.host or "")[:64] or None

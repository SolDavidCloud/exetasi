"""SlowAPI + Valkey integration.

Security notes:

- **Storage**: in production ``RATE_LIMIT_STORAGE_URI`` must point at a
  Valkey / Redis instance (``redis://…`` or ``rediss://…``). An in-process
  limiter across multiple uvicorn workers effectively multiplies an
  attacker's budget by ``--workers`` — config validation rejects that
  combination outright.
- **Transport**: prefer ``rediss://`` (TLS) for any non-loopback link.
  ``redis-py`` honours ``?ssl_cert_reqs=required&ssl_ca_certs=/path/ca.pem``
  in the URL querystring.
- **Auth**: always use username+password in the URI. The Valkey config
  under ``infra/valkey/valkey.conf`` neuters admin/destructive commands so
  a leaked credential still cannot wipe counters or reconfigure the
  server.
- **Algorithm**: ``moving-window`` avoids the boundary-flip burst that
  ``fixed-window`` allows (up to 2× the limit across the rollover).
- **Failure mode**: ``swallow_errors=False`` (fail-closed) by default. If
  Valkey is unreachable, requests error instead of silently bypassing the
  limiter. ``RATE_LIMIT_FAIL_OPEN=true`` flips to fail-open.
- **Per-IP vs per-user**: endpoints stack two ``@limiter.limit`` decorators
  — one keyed by IP, one keyed by the hashed session cookie. IP-only
  limits let a logged-in attacker with a rotating IP pool still burn
  resources on a single account; the session-keyed bucket plugs that gap.
  Unauthenticated requests fall back to IP for both.
- **Default ceiling**: ``default_limits`` installs a soft per-IP cap on
  every request routed through the middleware. It's the last line of
  defence against distributed low-and-slow floods — individual endpoints
  still have their own tighter caps on top.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import Request
from slowapi import Limiter

from app.api.deps import SESSION_COOKIE
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _ip(request: Request) -> str:
    settings = get_settings()
    if settings.trusted_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",", 1)[0].strip()
            if first:
                return first
    client = request.client
    return client.host if client else "unknown"


def ip_key(request: Request) -> str:
    """Per-client-IP bucket key."""

    return "ip:" + _ip(request)


def user_key(request: Request) -> str:
    """Per-authenticated-user bucket key with IP fallback.

    We hash the raw session cookie rather than store it verbatim so that
    bucket keys cannot be used to hijack a session even if an attacker can
    enumerate them (e.g. via a compromised Valkey). Unauthenticated
    requests fall back to the IP bucket so this decorator is always safe
    to stack on a route.
    """

    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        digest = hashlib.sha256(cookie.encode("utf-8")).hexdigest()[:16]
        return "u:" + digest
    return "ip:" + _ip(request)


def _is_shared_storage(uri: str) -> bool:
    return uri.startswith(("redis://", "rediss://", "redis+sentinel://"))


# Global per-IP ceiling applied to every request via SlowAPIMiddleware.
# Individual endpoints stack tighter per-endpoint + per-user limits on top.
_DEFAULT_LIMITS = ["600/minute"]


def _build_limiter() -> Limiter:
    settings = get_settings()
    storage_uri = settings.rate_limit_storage_uri

    kwargs: dict[str, object] = {
        "key_func": ip_key,
        "default_limits": _DEFAULT_LIMITS,
        "storage_uri": storage_uri,
        "strategy": settings.rate_limit_strategy,
        # ``swallow_errors`` semantics in slowapi: True logs+passes (fail
        # open), False re-raises (fail closed).
        "swallow_errors": settings.rate_limit_fail_open,
    }

    if _is_shared_storage(storage_uri):
        # ``limits.storage.RedisStorage`` supports a key prefix so multiple
        # apps can safely share a Valkey instance. Older limits releases
        # ignore unknown options, so this is safe across versions.
        kwargs["storage_options"] = {"prefix": settings.rate_limit_key_prefix}
    elif storage_uri.startswith("memory://") and not settings.is_dev:
        # Belt and braces: get_settings() already rejects this combination,
        # but re-check here so a future code path that bypasses validation
        # still fails loudly instead of silently running a non-shared
        # limiter in prod.
        logger.critical(
            "Refusing to build a rate limiter with memory:// storage in a "
            "non-dev environment."
        )
        raise RuntimeError("Refusing to use memory:// rate-limit storage in prod.")

    return Limiter(**kwargs)


limiter = _build_limiter()
"""Module-level limiter used via ``@limiter.limit(...)`` on endpoints.

IMPORTANT: decorated endpoints MUST accept ``request: Request`` as a
parameter — slowapi inspects the signature to find the current request.
"""

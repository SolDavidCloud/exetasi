"""Unit tests for the rate-limit key functions.

We can't easily drive slowapi itself in-process (the test suite disables
the limiter globally to avoid 127.0.0.1 collisions), so we test the key
functions directly. What we care about:

- ``ip_key`` ignores ``X-Forwarded-For`` unless ``TRUSTED_PROXY=true``.
- ``user_key`` hashes the session cookie rather than using it verbatim.
- ``user_key`` falls back to IP when there is no cookie.
- Different session cookies produce different bucket keys.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core import config as cfg_module
from app.core import ratelimit


def _request(
    *,
    host: str = "1.2.3.4",
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> SimpleNamespace:
    """Build the minimum quacks-like-a-Request shape the key funcs use."""

    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        cookies=cookies or {},
        headers=headers or {},
    )


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    cfg_module.get_settings.cache_clear()
    yield
    cfg_module.get_settings.cache_clear()


def test_ip_key_uses_client_host_when_proxy_not_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY", "false")
    cfg_module.get_settings.cache_clear()
    req = _request(host="10.0.0.1", headers={"x-forwarded-for": "9.9.9.9"})
    assert ratelimit.ip_key(req) == "ip:10.0.0.1"


def test_ip_key_honours_xff_when_proxy_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY", "true")
    monkeypatch.setenv("ENABLE_DEV_AUTH", "true")
    cfg_module.get_settings.cache_clear()
    req = _request(host="10.0.0.1", headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"})
    assert ratelimit.ip_key(req) == "ip:9.9.9.9"


def test_user_key_falls_back_to_ip_without_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY", "false")
    cfg_module.get_settings.cache_clear()
    req = _request(host="10.0.0.2")
    assert ratelimit.user_key(req) == "ip:10.0.0.2"


def test_user_key_hashes_session_cookie() -> None:
    req = _request(cookies={"exetasi_session": "super-secret-token"})
    key = ratelimit.user_key(req)
    assert key.startswith("u:")
    # The raw token must never appear in the bucket key.
    assert "super-secret-token" not in key
    # Truncated sha256 hex => 16 hex chars after the "u:" prefix.
    assert len(key) == 2 + 16


def test_user_key_distinguishes_sessions() -> None:
    a = ratelimit.user_key(_request(cookies={"exetasi_session": "alpha"}))
    b = ratelimit.user_key(_request(cookies={"exetasi_session": "beta"}))
    assert a != b

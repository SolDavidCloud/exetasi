"""Config-level assertions for the Valkey-backed rate limiter.

These tests don't hit a live Valkey — they verify that:

1. Production-like config without a shared rate-limit backend fails fast.
2. A Valkey URI is accepted.
3. memory:// is allowed only when ENABLE_DEV_AUTH=true.
"""

from __future__ import annotations

import pytest

from app.core import config as cfg_module


def _fresh_settings() -> cfg_module.Settings:
    cfg_module.get_settings.cache_clear()
    return cfg_module.get_settings()


def test_memory_storage_rejected_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEV_AUTH", "false")
    monkeypatch.setenv("SESSION_SECRET", "a-sufficiently-long-production-secret")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    cfg_module.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="RATE_LIMIT_STORAGE_URI=memory://"):
        cfg_module.get_settings()
    cfg_module.get_settings.cache_clear()


def test_valkey_storage_accepted_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEV_AUTH", "false")
    monkeypatch.setenv("SESSION_SECRET", "a-sufficiently-long-production-secret")
    monkeypatch.setenv(
        "RATE_LIMIT_STORAGE_URI",
        "rediss://app:pw@valkey.prod:6380/0?ssl_cert_reqs=required",
    )
    cfg_module.get_settings.cache_clear()
    s = cfg_module.get_settings()
    assert s.rate_limit_storage_uri.startswith("rediss://")
    assert s.rate_limit_fail_open is False
    assert s.rate_limit_strategy == "moving-window"
    cfg_module.get_settings.cache_clear()


def test_memory_storage_allowed_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DEV_AUTH", "true")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    cfg_module.get_settings.cache_clear()
    s = cfg_module.get_settings()
    assert s.rate_limit_storage_uri == "memory://"
    cfg_module.get_settings.cache_clear()

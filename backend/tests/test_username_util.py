"""Unit tests for the OAuth username sanitiser."""

from __future__ import annotations

from app.utils.username import sanitize_oauth_username


def test_strips_disallowed_characters() -> None:
    assert sanitize_oauth_username("Alice Wonderland!", fallback="u") == "AliceWonderland"


def test_preserves_allowed_punctuation() -> None:
    assert sanitize_oauth_username("alice.bob_42-x", fallback="u") == "alice.bob_42-x"


def test_drops_leading_punctuation() -> None:
    assert sanitize_oauth_username("...bob", fallback="u") == "bob"


def test_falls_back_when_cleanup_too_short() -> None:
    assert sanitize_oauth_username("!!", fallback="github_12345") == "github_12345"


def test_empty_input_uses_fallback() -> None:
    assert sanitize_oauth_username("", fallback="google_sub9") == "google_sub9"


def test_truncates_to_max_length() -> None:
    long = "a" * 200
    out = sanitize_oauth_username(long, fallback="u")
    assert len(out) == 64
    assert out == "a" * 64

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SESSION_SECRET = "dev-insecure-change-me"

RateLimitStrategy = Literal["fixed-window", "moving-window", "sliding-window-counter"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "exetasi"
    database_url: str = "postgresql+asyncpg://exetasi:exetasi@127.0.0.1:5432/exetasi"
    cors_origins: str = "http://localhost:9000,http://127.0.0.1:9000"
    session_secret: str = DEV_SESSION_SECRET
    frontend_origin: str = "http://127.0.0.1:9000"
    public_api_base_url: str = "http://127.0.0.1:8000"
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    gitlab_client_id: str = ""
    gitlab_client_secret: str = ""
    gitlab_oauth_base_url: str = "https://gitlab.com"
    enable_dev_auth: bool = False
    # When unset, derived from the scheme of frontend_origin so HTTPS
    # deployments get Secure cookies automatically.
    cookie_secure: bool | None = None
    # Only honour X-Forwarded-For when we know the backend is behind a
    # reverse proxy (e.g. nginx, ALB). Defaulting to False prevents an
    # attacker from spoofing audit-log IPs in dev.
    trusted_proxy: bool = False

    # -----------------------------------------------------------------
    # Rate limiting (slowapi + limits, backed by Valkey in production)
    # -----------------------------------------------------------------
    # Examples:
    #   memory://                                 (dev only — single process)
    #   redis://:pass@127.0.0.1:6379/0            (Valkey/Redis with auth)
    #   rediss://user:pass@valkey.prod:6380/0     (TLS; strongly recommended)
    # Any `redis://` or `rediss://` URI works against Valkey since the
    # RESP wire protocol is identical.
    rate_limit_storage_uri: str = "memory://"
    # moving-window is more accurate at window boundaries than fixed-window
    # (which can allow 2x burst when the window flips).
    rate_limit_strategy: RateLimitStrategy = "moving-window"
    # Fail CLOSED by default: if Valkey is unreachable, requests error out
    # rather than silently bypassing the limiter. Set to True only if the
    # availability cost of a Valkey outage outweighs the DoS risk.
    rate_limit_fail_open: bool = False
    # Keep exetasi's rate-limit keys in their own namespace so a shared
    # Valkey can also host caches, queues, etc. without collisions.
    rate_limit_key_prefix: str = "exetasi:rl"

    @property
    def session_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.frontend_origin.lower().startswith("https://")

    @property
    def is_dev(self) -> bool:
        """True when the app is running in an explicit development mode."""

        return self.enable_dev_auth


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Fail fast if a production deployment forgot to set a real secret.
    if s.session_secret == DEV_SESSION_SECRET and not s.is_dev:
        raise RuntimeError(
            "SESSION_SECRET must be configured outside of development "
            "(set ENABLE_DEV_AUTH=true only for local use).",
        )
    # Fail fast on an insecure rate-limit backend in production too.
    # An in-process limiter lets an attacker multiply their budget by the
    # number of workers, which is the whole reason we added Valkey.
    if s.rate_limit_storage_uri.startswith("memory://") and not s.is_dev:
        raise RuntimeError(
            "RATE_LIMIT_STORAGE_URI=memory:// is not allowed outside development. "
            "Point it at a Valkey (redis:// or rediss://) instance.",
        )
    return s

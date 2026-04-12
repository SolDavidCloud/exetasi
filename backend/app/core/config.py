from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "exetasi"
    database_url: str = "postgresql+asyncpg://exetasi:exetasi@127.0.0.1:5432/exetasi"
    cors_origins: str = "http://localhost:9000,http://127.0.0.1:9000"
    session_secret: str = "dev-insecure-change-me"
    frontend_origin: str = "http://127.0.0.1:9000"
    public_api_base_url: str = "http://127.0.0.1:8000"
    github_client_id: str = ""
    github_client_secret: str = ""
    enable_dev_auth: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

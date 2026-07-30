from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LABLENS_", env_file=".env", extra="ignore")

    env: Literal["development", "staging", "production"] = "development"
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite+aiosqlite:///./lablens.db"
    llm_provider: Literal["mock", "anthropic", "groq"] = "groq"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"
    groq_api_key: str | None = None
    groq_model: str = "llama3-8b-8192"
    upload_dir: str = "./uploads"
    cors_origins: str = "*"
    access_token_expire_minutes: int = 1440  # 24h
    max_upload_mb: int = 20

    @property
    def cors_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

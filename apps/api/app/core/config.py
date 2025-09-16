from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    jwt_secret: str
    postgres_dsn: str
    redis_url: str
    rabbitmq_url: str
    s3_endpoint: str
    s3_region: str = "eu-central-1"
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_public_url: str = "http://localhost:9000"
    api_base_url: str = "http://api:8080"
    public_api_url: str = "http://localhost:8080"
    cors_origins: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

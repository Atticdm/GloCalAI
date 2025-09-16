from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    app_env: str = "dev"
    service_name: str = "worker"
    postgres_dsn: str
    redis_url: str
    rabbitmq_url: str
    s3_endpoint: str
    s3_region: str = "eu-central-1"
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()  # type: ignore[call-arg]

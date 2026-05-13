import os
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    debug: bool = False

    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "pivot"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    milvus_uri: str = "./milvus.db"

    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_dim: int = 1536

    worker_poll_interval_seconds: float = 2.0
    worker_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=os.getenv("PIVOT_ENV_FILE", ".env.dev"),
        env_prefix="PIVOT_",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed_prefixes = ("mysql+pymysql://", "sqlite:///")
        if not value.startswith(allowed_prefixes):
            raise ValueError("database_url 必须以 mysql+pymysql:// 或 sqlite:/// 开头")
        return value

    @field_validator("server_port")
    @classmethod
    def validate_server_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("server_port 必须在 1-65535 范围内")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized_value = value.upper()
        if normalized_value not in VALID_LOG_LEVELS:
            raise ValueError(
                "log_level 必须是 DEBUG、INFO、WARNING、ERROR 或 CRITICAL"
            )
        return normalized_value

    @field_validator("embedding_dim")
    @classmethod
    def validate_embedding_dim(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("embedding_dim 必须大于 0")
        return value

    @model_validator(mode="after")
    def validate_prod_secret_key(self) -> "Settings":
        env_file = os.getenv("PIVOT_ENV_FILE", "")
        is_prod = Path(env_file).name == ".env.prod"
        unsafe_secret_keys = {"change-me-in-production", "CHANGE_ME"}
        if is_prod and self.jwt_secret_key in unsafe_secret_keys:
            raise ValueError("生产环境必须设置安全的 jwt_secret_key")
        return self


settings = Settings()

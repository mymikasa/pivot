import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://pivot:pivot_pass_2026@localhost:13306/pivot"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    debug: bool = False

    jwt_secret_key: str = "pivot-dev-jwt-secret-2026-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "pivot"
    jwt_audience: str = "user"

    minio_endpoint: str = "localhost:19000"
    minio_bucket: str = "pivot"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    milvus_uri: str = "./milvus.db"

    embedding_provider: str = "huggingface"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_dim: int = 512

    reranker_provider: str = ""
    reranker_model: str = ""

    worker_poll_interval_seconds: float = 2.0
    worker_enabled: bool = False

    model_config = SettingsConfigDict(
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
            raise ValueError("log_level 必须是 DEBUG、INFO、WARNING、ERROR 或 CRITICAL")
        return normalized_value

    @field_validator("embedding_dim")
    @classmethod
    def validate_embedding_dim(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("embedding_dim 必须大于 0")
        return value


def _parse_yaml_scalar(value: str) -> Any:
    normalized_value = value.strip()
    if not normalized_value:
        return ""
    if normalized_value in {"true", "True"}:
        return True
    if normalized_value in {"false", "False"}:
        return False
    if normalized_value in {"null", "Null", "~"}:
        return None
    if (
        len(normalized_value) >= 2
        and normalized_value[0] == normalized_value[-1]
        and normalized_value[0] in {'"', "'"}
    ):
        return normalized_value[1:-1]
    if normalized_value.startswith("[") and normalized_value.endswith("]"):
        raw_items = normalized_value[1:-1].strip()
        if not raw_items:
            return []
        return [_parse_yaml_scalar(item.strip()) for item in raw_items.split(",")]
    try:
        return int(normalized_value)
    except ValueError:
        pass
    try:
        return float(normalized_value)
    except ValueError:
        return normalized_value


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        if not line.startswith(" "):
            key, separator, value = stripped_line.partition(":")
            if not separator:
                raise ValueError(f"配置行缺少冒号：{line}")
            if value.strip():
                config[key] = _parse_yaml_scalar(value)
                current_section = None
                continue
            current_section = {}
            config[key] = current_section
            continue

        if current_section is None:
            raise ValueError(f"配置项缺少所属分组：{line}")
        key, separator, value = stripped_line.partition(":")
        if not separator:
            raise ValueError(f"配置行缺少冒号：{line}")
        current_section[key] = _parse_yaml_scalar(value)

    return config


def _settings_values_from_yaml(config: dict[str, Any]) -> dict[str, Any]:
    server = config.get("server", {})
    cors = config.get("cors", {})
    db = config.get("db", {})
    log = config.get("log", {})
    jwt = config.get("jwt", {})
    minio = config.get("minio", {})
    milvus = config.get("milvus", {})
    embedding = config.get("embedding", {})
    reranker = config.get("reranker", {})
    worker = config.get("worker", {})

    return {
        "database_url": db.get("url"),
        "server_host": server.get("host"),
        "server_port": server.get("port"),
        "cors_origins": cors.get("origins"),
        "log_level": log.get("level"),
        "debug": server.get("debug"),
        "jwt_secret_key": jwt.get("secret"),
        "jwt_algorithm": jwt.get("algorithm"),
        "jwt_issuer": jwt.get("issuer"),
        "jwt_audience": jwt.get("audience"),
        "minio_endpoint": minio.get("endpoint"),
        "minio_bucket": minio.get("bucket"),
        "minio_access_key": minio.get("access_key"),
        "minio_secret_key": minio.get("secret_key"),
        "minio_secure": minio.get("secure"),
        "milvus_uri": milvus.get("uri"),
        "embedding_model": embedding.get("model"),
        "embedding_provider": embedding.get("provider"),
        "embedding_api_key": embedding.get("api_key"),
        "embedding_api_base": embedding.get("api_base"),
        "embedding_dim": embedding.get("dim"),
        "reranker_provider": reranker.get("provider"),
        "reranker_model": reranker.get("model"),
        "worker_poll_interval_seconds": worker.get("poll_interval_seconds"),
        "worker_enabled": worker.get("enabled"),
    }


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path or os.getenv("PIVOT_CONFIG_FILE", DEFAULT_CONFIG_PATH))
    values = _settings_values_from_yaml(_load_simple_yaml(path))
    return Settings(**{key: value for key, value in values.items() if value is not None})


settings = load_settings()

import pytest
from pydantic import ValidationError

from src.core.config import Settings, load_settings


def test_settings_accepts_valid_values():
    settings = Settings(
        database_url="sqlite:///:memory:",
        server_port=8080,
        cors_origins=["http://localhost:5173"],
        log_level="debug",
    )

    assert settings.server_port == 8080
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_rejects_invalid_port():
    with pytest.raises(ValidationError, match="server_port"):
        Settings(server_port=65536)


def test_settings_rejects_invalid_log_level():
    with pytest.raises(ValidationError, match="log_level"):
        Settings(log_level="TRACE")


def test_settings_rejects_invalid_database_url():
    with pytest.raises(ValidationError, match="database_url"):
        Settings(database_url="postgresql://pivot:secret@localhost/pivot")


def test_settings_accepts_parse_service_values():
    settings = Settings(
        database_url="sqlite:///:memory:",
        server_port=8080,
        cors_origins=["http://localhost:5174"],
        jwt_secret_key="test-secret",
        minio_endpoint="localhost:19000",
        minio_bucket="pivot",
        embedding_dim=8,
    )

    assert settings.database_url == "sqlite:///:memory:"
    assert settings.jwt_secret_key == "test-secret"
    assert settings.minio_bucket == "pivot"
    assert settings.embedding_dim == 8


def test_load_settings_reads_yaml_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
server:
  host: "127.0.0.1"
  port: 8010
db:
  url: "mysql+pymysql://pivot:pivot_pass_2026@localhost:13306/pivot"
log:
  level: "debug"
jwt:
  secret: "yaml-secret"
  issuer: "pivot"
  audience: "user"
minio:
  endpoint: "localhost:19000"
  bucket: "pivot"
  access_key: "minioadmin"
  secret_key: "minioadmin"
  secure: false
milvus:
  uri: "./milvus.db"
embedding:
  model: "text-embedding-3-small"
  api_key: ""
  api_base: "https://api.openai.com/v1"
  dim: 1536
worker:
  poll_interval_seconds: 1.5
  enabled: true
""",
        encoding="utf-8",
    )

    settings = load_settings(config_file)

    assert settings.database_url == (
        "mysql+pymysql://pivot:pivot_pass_2026@localhost:13306/pivot"
    )
    assert settings.server_host == "127.0.0.1"
    assert settings.server_port == 8010
    assert settings.log_level == "DEBUG"
    assert settings.jwt_secret_key == "yaml-secret"
    assert settings.jwt_issuer == "pivot"
    assert settings.jwt_audience == "user"
    assert settings.minio_endpoint == "localhost:19000"
    assert settings.worker_poll_interval_seconds == 1.5
    assert settings.worker_enabled is True

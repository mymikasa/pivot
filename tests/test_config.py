import os

import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_accepts_valid_values():
    settings = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret_key="test-secret",
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


def test_settings_rejects_default_secret_key_in_prod(monkeypatch):
    monkeypatch.setenv("PIVOT_ENV_FILE", os.fspath(".env.prod"))

    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(jwt_secret_key="CHANGE_ME")

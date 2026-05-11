from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_and_verify():
    plain = "mypassword123"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token(subject="1")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="1")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["type"] == "refresh"


def test_decode_invalid_token_returns_none():
    result = decode_token("invalid.token.here")
    assert result is None

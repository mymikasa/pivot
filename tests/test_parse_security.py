from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from src.core.security import AuthenticatedUser, decode_access_token


def test_decode_access_token_returns_user():
    token = jwt.encode(
        {
            "sub": "123",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "test-secret",
        algorithm="HS256",
    )

    user = decode_access_token(token, secret="test-secret", algorithm="HS256")

    assert user == AuthenticatedUser(user_id=123, role="admin")


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        decode_access_token("bad.token", secret="test-secret", algorithm="HS256")

    assert exc.value.status_code == 401

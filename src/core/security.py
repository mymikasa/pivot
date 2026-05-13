from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, status
import bcrypt
import jwt

from src.core.config import settings


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    role: str


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "type": "access", "jti": uuid4().hex}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh", "jti": uuid4().hex}
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None


def decode_access_token(
    token: str,
    *,
    secret: str,
    algorithm: str,
) -> AuthenticatedUser:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("missing sub")
        return AuthenticatedUser(
            user_id=int(subject),
            role=str(payload.get("role", "user")),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的访问令牌",
        ) from exc

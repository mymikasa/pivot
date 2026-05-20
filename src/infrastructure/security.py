from dataclasses import dataclass

from fastapi import HTTPException, status
import jwt


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    role: str


def decode_access_token(
    token: str,
    *,
    secret: str,
    algorithm: str,
    issuer: str,
    audience: str,
) -> AuthenticatedUser:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            issuer=issuer,
            audience=audience,
        )
        if payload.get("typ") != "access":
            raise ValueError("wrong token type")
        subject = payload.get("sub") or payload.get("uid")
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

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security import AuthenticatedUser, decode_access_token


bearer_scheme = HTTPBearer(auto_error=True)


def get_current_parse_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    return decode_access_token(
        credentials.credentials,
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


__all__ = ["get_current_parse_user", "get_db"]

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings

# Argon2 password hasher (recommended by OWASP)
pwd_context = PasswordHash((Argon2Hasher(),))

# OAuth2 scheme for Swagger UI & bearer authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates an Argon2 hash from a plain password."""
    return pwd_context.hash(password)


def create_access_token(user_id: int, extra_claims: dict[str, Any] | None = None) -> str:
    """Creates a signed JWT access token with short expiration."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int, token_jti: str) -> tuple[str, datetime]:
    """Creates a signed JWT refresh token with unique jti and longer expiration."""
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": token_jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token_str = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token_str, expire


def decode_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration.

    Raises:
        jwt.PyJWTError if the token is invalid or expired.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["exp", "sub", "type"]},
    )

"""Security utilities for password hashing and JWT handling.

This module provides functions to securely hash passwords using
``passlib`` and to generate and verify JWT tokens via ``python-jose``.

Usage:
    from app.core.security import get_password_hash, verify_password, create_access_token

Passwords are hashed using the Bcrypt algorithm. The JWT token
generation uses the secret and algorithm defined in settings.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


# Password hashing context using Bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: The unhashed user-provided password.
        hashed_password: The stored hashed password.
    Returns:
        True if the password matches, otherwise False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Bcrypt.

    Args:
        password: The plain password to hash.
    Returns:
        The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Any, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a new JWT access token.

    Args:
        subject: The token subject (e.g. user identifier). Can be any JSON
            serialisable type.
        expires_delta: Optional timedelta controlling token expiration. If
            omitted, the default expiry defined in settings is used.
    Returns:
        A signed JWT token as a string.
    """
    settings = get_settings()
    if expires_delta is not None:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt



def decode_access_token(token: str) -> Optional[str]:
    """Decode a JWT access token and return the subject if valid.

    Args:
        token: The JWT token to decode.
    Returns:
        The subject (user identifier) if valid, otherwise None.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None
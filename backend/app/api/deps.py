"""API dependencies for authentication and database sessions."""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import models
from app.db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """Retrieve the current authenticated user based on the JWT token.

    Args:
        token: The bearer token from the Authorization header.
        db: Database session dependency.
    Returns:
        The user model associated with the token subject.
    Raises:
        HTTPException: When the token is invalid or user does not exist.
    """
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """Ensure that the authenticated user has admin role.

    Args:
        user: The current user dependency.
    Returns:
        The same user if they are an admin.
    Raises:
        HTTPException: If the user is not an admin.
    """
    if user.role != models.Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user
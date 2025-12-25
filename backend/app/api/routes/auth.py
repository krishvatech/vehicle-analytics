"""Authentication routes for login and token generation."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.db import models
from app.db.session import get_db
from app.schemas.auth import Token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate a user and return a JWT access token.

    Uses username and password via OAuth2PasswordRequestForm. On
    successful authentication, returns a JWT token which can be used
    for authenticated requests.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
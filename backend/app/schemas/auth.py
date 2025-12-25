"""Authentication schemas for login and token responses."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Response schema for access tokens."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Type of the token")


class TokenData(BaseModel):
    """Payload contained within a token after decoding."""

    username: str | None = None
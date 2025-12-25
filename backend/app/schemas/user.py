"""Schemas related to users."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Role


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=4)
    role: Role = Field(default=Role.viewer)


class UserOut(UserBase):
    id: int
    role: Role
    created_at: datetime

    class Config:
        orm_mode = True
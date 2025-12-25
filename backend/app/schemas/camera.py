"""Schemas for camera CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, AnyHttpUrl


class CameraBase(BaseModel):
    name: str = Field(..., max_length=100)
    rtsp_url: str = Field(..., max_length=500)
    is_active: bool = True


class CameraCreate(CameraBase):
    gate_id: int = Field(..., description="Gate identifier to which the camera belongs")


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    rtsp_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class CameraOut(CameraBase):
    id: int
    gate_id: int
    last_seen: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True
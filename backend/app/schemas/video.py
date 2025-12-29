"""Schemas for video upload and listing."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoOut(BaseModel):
    id: int
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    mime_type: str
    size_bytes: int
    status: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True

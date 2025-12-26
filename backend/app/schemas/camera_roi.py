"""Schemas for camera ROI configuration."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CameraROIBase(BaseModel):
    x: float = Field(..., ge=0, le=1, alias="roi_x")
    y: float = Field(..., ge=0, le=1, alias="roi_y")
    w: float = Field(..., gt=0, le=1, alias="roi_w")
    h: float = Field(..., gt=0, le=1, alias="roi_h")
    coordinate_type: str = Field(default="normalized")

    class Config:
        allow_population_by_field_name = True


class CameraROIOut(CameraROIBase):
    id: int
    camera_id: int
    updated_by_id: Optional[int] = None
    updated_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

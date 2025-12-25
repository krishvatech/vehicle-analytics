"""Schemas for ROI definitions."""

from datetime import datetime
from typing import List, Tuple

from pydantic import BaseModel, Field


class ROICreate(BaseModel):
    gate_id: int
    camera_id: int
    shape: str = Field(default="polygon", description="Shape type: rectangle or polygon")
    coordinates: List[List[float]] = Field(
        ..., description="List of [x, y] pairs defining the ROI polygon"
    )


class ROIOut(ROICreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
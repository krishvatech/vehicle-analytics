"""Schemas related to event logging and outputs."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import EntryExit, VehicleType


class EventBase(BaseModel):
    gate_id: int
    camera_id: int
    entry_exit: EntryExit
    vehicle_type: Optional[VehicleType] = None
    timestamp: datetime
    event_uuid: str
    plate_number: Optional[str] = None
    barcode_value: Optional[str] = None
    material_type: Optional[str] = None
    material_confidence: Optional[float] = None
    load_percentage: Optional[float] = None
    load_label: Optional[str] = None
    snapshot_path: Optional[str] = None
    load_crop_path: Optional[str] = None
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None
    edit_reason: Optional[str] = None


class EventOut(EventBase):
    id: int
    track_id: Optional[int]
    confidence: Optional[float]
    created_at: datetime

    class Config:
        orm_mode = True


class EventCorrection(BaseModel):
    plate_number: Optional[str] = None
    barcode_value: Optional[str] = None
    material_type: Optional[str] = None
    load_percentage: Optional[float] = None


class EventTags(BaseModel):
    material_type: Optional[str] = None
    material_confidence: Optional[float] = None
    load_percentage: Optional[float] = None
    load_label: Optional[str] = None
    edit_reason: Optional[str] = None


class EventFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    gate_id: Optional[int] = None
    vehicle_type: Optional[VehicleType] = None
    entry_exit: Optional[EntryExit] = None

"""Event API endpoints for listing and correcting event data."""

import csv
from datetime import datetime
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models
from app.db.session import get_db
from app.schemas import event as schema
from datetime import datetime


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=List[schema.EventOut])
def list_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    gate_id: Optional[int] = None,
    vehicle_type: Optional[models.VehicleType] = None,
    entry_exit: Optional[models.EntryExit] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """List events with optional filters."""
    query = db.query(models.Event)
    if start_date:
        query = query.filter(models.Event.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Event.timestamp <= end_date)
    if gate_id:
        query = query.filter(models.Event.gate_id == gate_id)
    if vehicle_type:
        query = query.filter(models.Event.vehicle_type == vehicle_type)
    if entry_exit:
        query = query.filter(models.Event.entry_exit == entry_exit)
    events = query.order_by(models.Event.timestamp.desc()).all()
    return events


@router.patch("/{event_id}", response_model=schema.EventOut)
def correct_event(
    event_id: int,
    correction: schema.EventCorrection,
    db: Session = Depends(get_db),
    user: models.User = Depends(deps.get_current_user),
):
    """Apply manual corrections to an event."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    data = correction.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(event, key, value)
    # Add audit fields
    event.processed = True
    db.commit()
    db.refresh(event)
    return event


@router.get("/export")
def export_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """Export events to CSV and return as a file attachment."""
    query = db.query(models.Event)
    if start_date:
        query = query.filter(models.Event.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Event.timestamp <= end_date)
    events = query.order_by(models.Event.timestamp.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "gate_id",
        "camera_id",
        "entry_exit",
        "vehicle_type",
        "plate_number",
        "barcode_value",
        "material_type",
        "load_percentage",
        "snapshot_path",
    ])
    for e in events:
        writer.writerow([
            e.timestamp,
            e.gate_id,
            e.camera_id,
            e.entry_exit.value,
            e.vehicle_type.value if e.vehicle_type else None,
            e.plate_number,
            e.barcode_value,
            e.material_type,
            e.load_percentage,
            e.snapshot_path,
        ])
    csv_content = output.getvalue()
    headers = {
        "Content-Disposition": "attachment; filename=events.csv",
        "Content-Type": "text/csv",
    }
    return Response(content=csv_content, media_type="text/csv", headers=headers)


@router.post("/{event_id}/tags", response_model=schema.EventOut)
def tag_event(
    event_id: int,
    tags: schema.EventTags,
    db: Session = Depends(get_db),
    user: models.User = Depends(deps.get_current_user),
):
    """Manually tag material/load and record editor."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if tags.material_type is not None:
        event.material_type = tags.material_type
    if tags.material_confidence is not None:
        event.material_confidence = tags.material_confidence
    if tags.load_percentage is not None:
        event.load_percentage = tags.load_percentage
        # update label
        lp = float(tags.load_percentage)
        if lp < 25:
            event.load_label = "Empty"
        elif lp < 50:
            event.load_label = "Partial"
        elif lp < 75:
            event.load_label = "Half"
        else:
            event.load_label = "Full"
    if tags.load_label is not None:
        event.load_label = tags.load_label
    event.edited_by = user.username
    event.edited_at = datetime.utcnow()
    event.edit_reason = tags.edit_reason
    db.commit()
    db.refresh(event)
    return event

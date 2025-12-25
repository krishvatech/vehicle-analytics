"""ROI API endpoints for saving and retrieving gate regions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models
from app.db.session import get_db
from app.schemas import roi as schema


router = APIRouter(prefix="/rois", tags=["rois"])


@router.post("/", response_model=schema.ROIOut)
def create_roi(
    roi_in: schema.ROICreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.require_admin),
):
    """Create or update the ROI for a gate/camera combination."""
    # Check if gate and camera exist
    gate = db.query(models.Gate).filter(models.Gate.id == roi_in.gate_id).first()
    camera = db.query(models.Camera).filter(models.Camera.id == roi_in.camera_id).first()
    if not gate or not camera:
        raise HTTPException(status_code=404, detail="Gate or camera not found")
    # Delete existing ROI for this gate and camera
    existing = (
        db.query(models.ROI)
        .filter(models.ROI.gate_id == roi_in.gate_id, models.ROI.camera_id == roi_in.camera_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    roi = models.ROI(
        gate_id=roi_in.gate_id,
        camera_id=roi_in.camera_id,
        shape=roi_in.shape,
        coordinates=roi_in.coordinates,
    )
    db.add(roi)
    db.commit()
    db.refresh(roi)
    return roi


@router.get("/{gate_id}/{camera_id}", response_model=schema.ROIOut)
def get_roi(
    gate_id: int,
    camera_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """Retrieve the ROI for a given gate and camera."""
    roi = (
        db.query(models.ROI)
        .filter(models.ROI.gate_id == gate_id, models.ROI.camera_id == camera_id)
        .first()
    )
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")
    return roi
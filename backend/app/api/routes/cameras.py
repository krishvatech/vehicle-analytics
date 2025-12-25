"""Camera CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models
from app.db.session import get_db
from app.schemas import camera as schema


router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("/", response_model=schema.CameraOut)
def create_camera(
    camera_in: schema.CameraCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.require_admin),
):
    """Create a new camera and attach it to a gate."""
    gate = db.query(models.Gate).filter(models.Gate.id == camera_in.gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    camera = models.Camera(
        gate_id=camera_in.gate_id,
        name=camera_in.name,
        rtsp_url=camera_in.rtsp_url,
        is_active=camera_in.is_active,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.get("/", response_model=list[schema.CameraOut])
def list_cameras(
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """List all cameras."""
    return db.query(models.Camera).all()


@router.get("/{camera_id}", response_model=schema.CameraOut)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """Retrieve a single camera by its ID."""
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.put("/{camera_id}", response_model=schema.CameraOut)
def update_camera(
    camera_id: int,
    camera_in: schema.CameraUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.require_admin),
):
    """Update an existing camera."""
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    for attr, value in camera_in.dict(exclude_unset=True).items():
        setattr(camera, attr, value)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.require_admin),
):
    """Delete a camera."""
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()
    return {"detail": "Camera deleted"}


@router.get("/{camera_id}/snapshot")
def get_snapshot(
    camera_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """Return a single frame snapshot for the camera.

    This endpoint reads the sample video associated with the camera
    (defined via ``SAMPLE_VIDEO_PATH`` environment variable) and
    returns the first frame as a JPEG image. It is used by the
    frontend ROI setup screen.
    """
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    video_path = os.getenv("SAMPLE_VIDEO_PATH", "/sample_media/sample.mp4")
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise HTTPException(status_code=500, detail="Unable to capture snapshot")
    # Encode frame to JPEG
    ret, jpeg = cv2.imencode(".jpg", frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode snapshot")
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")


@router.get("/{camera_id}/mjpeg")
def mjpeg_preview(
    camera_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    """Return a simple MJPEG preview stream from the sample video (local-only)."""
    camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    video_path = os.getenv("SAMPLE_VIDEO_PATH", "/sample_media/sample.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=500, detail="Sample video missing")

    def gen():
        cap = cv2.VideoCapture(video_path)
        while True:
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            ok, jpeg = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

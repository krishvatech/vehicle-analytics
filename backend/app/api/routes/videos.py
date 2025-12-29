"""Video upload and retrieval API endpoints."""

import os
import uuid
from typing import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import models
from app.db.session import get_db
from app.schemas import video as schema


router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
ALLOWED_EXTENSIONS = {".mp4", ".webm"}


def _resolve_user_from_request(
    db: Session,
    request: Request,
    token: str | None,
) -> models.User:
    auth_header = request.headers.get("authorization")
    bearer = None
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer = auth_header.split(" ", 1)[1]
    raw_token = token or bearer
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = decode_access_token(raw_token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def _iter_file(path: str, start: int = 0, end: int | None = None) -> Iterator[bytes]:
    with open(path, "rb") as handle:
        handle.seek(start)
        remaining = end - start + 1 if end is not None else None
        chunk_size = 1024 * 1024
        while True:
            read_size = chunk_size if remaining is None else min(chunk_size, remaining)
            data = handle.read(read_size)
            if not data:
                break
            if remaining is not None:
                remaining -= len(data)
            yield data


def _resolve_extension(upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if upload.content_type in ALLOWED_VIDEO_TYPES:
        return ALLOWED_VIDEO_TYPES[upload.content_type]
    if upload.content_type == "application/octet-stream" and ext in ALLOWED_EXTENSIONS:
        return ext
    raise HTTPException(status_code=400, detail="Invalid file type. Allowed: mp4, webm")


@router.post("/", response_model=schema.VideoOut)
async def upload_video(
    title: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(deps.require_admin),
):
    settings = get_settings()
    extension = _resolve_extension(file)

    upload_dir = settings.VIDEO_UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    target_path = os.path.join(upload_dir, filename)

    max_bytes = settings.VIDEO_MAX_SIZE_MB * 1024 * 1024
    size = 0
    try:
        with open(target_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Max={settings.VIDEO_MAX_SIZE_MB} MB",
                    )
                out.write(chunk)
    except HTTPException:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise
    finally:
        await file.close()

    mime_type = file.content_type
    if mime_type == "application/octet-stream":
        mime_type = "video/mp4" if extension == ".mp4" else "video/webm"

    video = models.Video(
        title=title,
        description=description,
        file_path=target_path,
        mime_type=mime_type,
        size_bytes=size,
        uploaded_by_id=user.id,
        status="uploaded",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@router.get("/", response_model=list[schema.VideoOut])
def list_videos(
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    return db.query(models.Video).order_by(models.Video.created_at.desc()).all()


@router.get("/{video_id}", response_model=schema.VideoOut)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_user),
):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/file")
def get_video_file(
    video_id: int,
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    _resolve_user_from_request(db, request, token)
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not os.path.exists(video.file_path):
        raise HTTPException(status_code=404, detail="Video file missing")

    file_size = os.path.getsize(video.file_path)
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(video.file_path, media_type=video.mime_type)

    try:
        _, range_spec = range_header.split("=")
        start_str, end_str = range_spec.split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid range header")

    start = max(0, start)
    end = min(end, file_size - 1)
    if start > end:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
    }
    return StreamingResponse(
        _iter_file(video.file_path, start=start, end=end),
        status_code=206,
        headers=headers,
        media_type=video.mime_type,
    )

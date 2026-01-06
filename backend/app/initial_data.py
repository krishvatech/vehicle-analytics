"""Populate the database with initial data for local development.

Running this module will insert a default admin user, a demo project,
a gate and a camera into the database if they do not already exist.

IMPORTANT:
- The demo camera ("Office Camera") is seeded ONLY when there are NO cameras in DB.
  This prevents it from auto-adding after you manually create cameras.

This script is invoked from the Docker container entrypoint to ensure the DB
is pre-populated on first run.
"""

import os
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db import models
from app.db.session import engine, SessionLocal


def init_data(db: Session) -> None:
    # Create admin user if not exists
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin = models.User(
            username="admin",
            hashed_password=get_password_hash("admin"),
            role=models.Role.admin,
        )
        db.add(admin)
        print("Seeded admin user with username=admin and password=admin")

    # Create demo project
    project = db.query(models.Project).filter(models.Project.name == "Demo Project").first()
    if not project:
        project = models.Project(name="Demo Project")
        db.add(project)
        print("Seeded demo project")
    db.commit()
    db.refresh(project)

    # Create gate
    gate = db.query(models.Gate).filter(models.Gate.name == "Main Gate").first()
    if not gate:
        gate = models.Gate(
            name="Main Gate",
            project_id=project.id,
            anpr_enabled=True,
            barcode_enabled=False,
        )
        db.add(gate)
        print("Seeded main gate")
    db.commit()
    db.refresh(gate)

    # -----------------------------
    # Seed demo camera ONLY on fresh DB
    # -----------------------------
    any_camera = db.query(models.Camera.id).first()  # None if no cameras exist
    camera = db.query(models.Camera).filter(models.Camera.name == "Office Camera").first()

    # If there are no cameras at all, seed the demo camera
    if not any_camera and not camera:
        # Default points to mediamtx RTSP stream inside docker network.
        # Override by setting DEMO_CAMERA_RTSP_URL in .env if needed.
        rtsp_url = f"file://{os.getenv('SAMPLE_VIDEO_PATH', '/sample_media/sample.mp4')}"

        camera = models.Camera(
            name="Office Camera",
            gate_id=gate.id,
            rtsp_url=rtsp_url,
            is_active=True,
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        print("Seeded office camera")
    else:
        db.commit()

    # Seed default ROI only if the demo camera exists
    if camera:
        existing_roi = (
            db.query(models.ROI)
            .filter(models.ROI.gate_id == gate.id, models.ROI.camera_id == camera.id)
            .first()
        )
        if not existing_roi:
            roi = models.ROI(
                gate_id=gate.id,
                camera_id=camera.id,
                shape="rectangle",
                coordinates=[[200, 150], [440, 330]],
            )
            db.add(roi)
            print("Seeded default ROI for office camera")
            db.commit()


def main() -> None:
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()

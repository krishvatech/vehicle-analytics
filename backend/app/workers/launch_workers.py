"""Launch stream processing tasks for all active cameras.

This helper enumerates active cameras in the database and dispatches
Celery tasks to process their streams. It can be invoked as part of
the worker container's startup command.
"""

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db import models


def launch_all() -> None:
    db = SessionLocal()
    try:
        cameras = db.query(models.Camera).filter(models.Camera.is_active == True).all()
        for camera in cameras:
            celery_app.send_task("app.workers.tasks.process_camera_stream", args=[camera.id])
        print(f"Dispatched stream processing tasks for {len(cameras)} cameras")
    finally:
        db.close()


if __name__ == "__main__":
    launch_all()
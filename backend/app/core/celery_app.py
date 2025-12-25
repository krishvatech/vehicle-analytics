"""Celery application instance and configuration.

The Celery app is responsible for executing asynchronous tasks such as
processing camera streams and sending notifications. The broker and
backend are configured to use Redis based on the application settings.
"""

from celery import Celery

from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "worker",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
)

celery_app.conf.update(
    task_routes={
        "app.workers.tasks.process_camera_stream": {"queue": "streams"},
        "app.workers.tasks.send_notification": {"queue": "notifications"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
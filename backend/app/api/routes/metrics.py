"""Basic metrics/health counters."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.services import metrics as m

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/liveness")
def liveness():
    return {"status": "ok"}


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)):
    # simple DB check
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/prometheus")
def prometheus_metrics(db: Session = Depends(get_db)):
    """Expose a minimal Prometheus text metrics snapshot."""
    event_count = db.query(models.Event).count()
    camera_count = db.query(models.Camera).count()
    gate_count = db.query(models.Gate).count()
    lines = []
    # counters
    for (gate, vtype, direction), val in m.events_total.items():
        lines.append(f'vehicle_events_total{{gate="{gate}",vehicle_type="{vtype}",direction="{direction}"}} {val}')
    for (channel, status), val in m.notifications_sent_total.items():
        lines.append(f'notifications_sent_total{{channel="{channel}",status="{status}"}} {val}')
    for cam, val in m.stream_errors_total.items():
        lines.append(f'stream_errors_total{{camera="{cam}"}} {val}')
    body = (
        f"# HELP vehicle_events_total Total number of vehicle events\n"
        f"# TYPE vehicle_events_total counter\n"
        f"vehicle_events_total {event_count}\n"
        f"# HELP cameras_total Total cameras\n"
        f"# TYPE cameras_total gauge\n"
        f"cameras_total {camera_count}\n"
        f"# HELP gates_total Total gates\n"
        f"# TYPE gates_total gauge\n"
        f"gates_total {gate_count}\n"
        + "\n".join(lines)
    )
    return Response(content=body, media_type="text/plain")

"""Notification rules API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models
from app.db.models import NotificationRule, NotificationChannel
from app.db.session import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[dict])
def list_rules(db: Session = Depends(get_db), _: models.User = Depends(deps.require_admin)):
    rules = db.query(NotificationRule).all()
    return [
        {
            "id": r.id,
            "gate_id": r.gate_id,
            "project_id": r.project_id,
            "channel": r.channel.value,
            "enabled": r.enabled,
            "min_confidence": r.min_confidence,
            "directions": r.directions.split(",") if r.directions else [],
            "vehicle_types": r.vehicle_types.split(",") if r.vehicle_types else [],
            "recipients": r.recipient_list(),
        }
        for r in rules
    ]


@router.post("/", response_model=dict)
def upsert_rule(
    gate_id: int,
    channel: NotificationChannel,
    enabled: bool = True,
    min_confidence: int = 0,
    recipients: str | None = None,
    project_id: int | None = None,
    directions: str | None = None,
    vehicle_types: str | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.require_admin),
):
    rule = (
        db.query(NotificationRule)
        .filter(NotificationRule.gate_id == gate_id, NotificationRule.channel == channel)
        .first()
    )
    if not rule:
        rule = NotificationRule(gate_id=gate_id, channel=channel)
    rule.enabled = enabled
    rule.min_confidence = min_confidence
    rule.recipients = recipients
    rule.project_id = project_id
    rule.directions = directions
    rule.vehicle_types = vehicle_types
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "id": rule.id,
        "gate_id": rule.gate_id,
        "channel": rule.channel.value,
        "enabled": rule.enabled,
        "min_confidence": rule.min_confidence,
        "directions": rule.directions.split(",") if rule.directions else [],
        "vehicle_types": rule.vehicle_types.split(",") if rule.vehicle_types else [],
        "recipients": rule.recipient_list(),
    }


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db), _: models.User = Depends(deps.require_admin)):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"detail": "deleted"}

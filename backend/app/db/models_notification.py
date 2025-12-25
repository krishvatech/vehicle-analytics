"""Notification rule models."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    push = "push"


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=True)
    channel = Column(Enum(NotificationChannel), nullable=False, default=NotificationChannel.email)
    enabled = Column(Boolean, default=True, nullable=False)
    min_confidence = Column(Integer, default=0, nullable=False)
    recipients = Column(String(512), nullable=True)  # comma-separated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def recipient_list(self):
        if not self.recipients:
            return []
        return [r.strip() for r in self.recipients.split(",") if r.strip()]

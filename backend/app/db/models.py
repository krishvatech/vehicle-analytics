"""Database models for the CCTV vehicle analytics system.

The models defined here reflect the core domain objects such as
users, projects, gates, cameras, ROI definitions and events. Each
table is represented as a SQLAlchemy ORM class. Relationships use
lazy-loading where appropriate to avoid N+1 queries.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Boolean,
    JSON,
    UniqueConstraint,
    Text,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Role(str, enum.Enum):
    """User roles supported by the system."""

    admin = "admin"
    viewer = "viewer"


class EntryExit(str, enum.Enum):
    """Direction of a vehicle crossing."""

    entry = "ENTRY"
    exit = "EXIT"


class VehicleType(str, enum.Enum):
    """Supported vehicle classifications."""

    truck = "Truck"
    dumper = "Dumper"
    car = "Car/4-wheeler"
    bike = "Bike/2-wheeler"
    tractor = "Tractor/Trolley"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.admin)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    gates = relationship("Gate", back_populates="project", cascade="all, delete-orphan")

class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    push = "push"


class Gate(Base):
    __tablename__ = "gates"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uix_project_gate"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    anpr_enabled = Column(Boolean, default=True)
    barcode_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="gates")
    cameras = relationship("Camera", back_populates="gate", cascade="all, delete-orphan")
    rois = relationship("ROI", back_populates="gate", cascade="all, delete-orphan")


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (UniqueConstraint("gate_id", "name", name="uix_gate_camera"),)

    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    name = Column(String(100), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    gate = relationship("Gate", back_populates="cameras")
    rois = relationship("ROI", back_populates="camera", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="camera")


class ROI(Base):
    __tablename__ = "rois"
    __table_args__ = (UniqueConstraint("gate_id", "camera_id", name="uix_gate_camera_roi"),)

    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    shape = Column(String(20), default="polygon")  # rectangle or polygon
    coordinates = Column(JSON, nullable=False)  # list of points [[x,y], ...]
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    gate = relationship("Gate", back_populates="rois")
    camera = relationship("Camera", back_populates="rois")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    entry_exit = Column(Enum(EntryExit), nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=True)
    track_id = Column(Integer, nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    plate_number = Column(String(50), nullable=True)
    barcode_value = Column(String(100), nullable=True)
    material_type = Column(String(50), nullable=True)
    material_confidence = Column(Numeric(5, 2), nullable=True)
    load_percentage = Column(Numeric(5, 2), nullable=True)
    load_label = Column(String(32), nullable=True)
    snapshot_path = Column(String(500), nullable=True)
    load_crop_path = Column(String(500), nullable=True)
    processed = Column(Boolean, default=False)
    edited_by = Column(String(64), nullable=True)
    edited_at = Column(DateTime, nullable=True)
    edit_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    camera = relationship("Camera", back_populates="events")
    gate = relationship("Gate")


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=True)
    channel = Column(Enum(NotificationChannel), nullable=False, default=NotificationChannel.email)
    enabled = Column(Boolean, default=True, nullable=False)
    min_confidence = Column(Integer, default=0, nullable=False)
    directions = Column(String(32), nullable=True)  # comma list of ENTRY/EXIT
    vehicle_types = Column(String(128), nullable=True)  # comma list
    recipients = Column(String(512), nullable=True)  # comma-separated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def recipient_list(self):
        if not self.recipients:
            return []
        return [r.strip() for r in self.recipients.split(",") if r.strip()]

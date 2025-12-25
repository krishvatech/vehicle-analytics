"""Celery tasks for stream processing and notifications."""

import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2
from celery import shared_task
from sqlalchemy.orm import Session
import requests

from app.core.config import get_settings
from app.core.celery_app import celery_app
from app.db import models
from app.db.session import SessionLocal
from app.services.detection.stub_detector import detect_vehicles
from app.services.detection.yolo_detector import YOLODetector
from app.services.detection.plate_detector import PlateDetector
from app.services.detection.identification import identify_from_crop
from app.services.analytics.tracker import TrackManager
from app.services.analytics.gate_logic import point_inside_rect, determine_entry_exit
from app.services.analytics.material_base import DeterministicEstimator
from app.services.analytics.material_model import MaterialModelEstimator
from app.services.storage.minio_client import MinioService
from app.services import metrics as m
from app.db.models import NotificationRule, NotificationChannel


settings = get_settings()

# Prevent spamming events: {(camera_id, track_id): last_event_timestamp}
_last_event_time: dict[tuple[int, int], float] = {}
# Debounce notifications per (gate, channel)
_last_notify_time: dict[tuple[int, str], float] = {}


def _identify_vehicle(frame, bbox, mode: str, plate_detector=None, plate_conf: float = 0.35):
    """Identify plate/barcode from vehicle crop using OCR/decoder; graceful fallback."""
    x1, y1, x2, y2 = map(int, bbox)
    x1 = max(0, x1); y1 = max(0, y1)
    crop = frame[y1:max(y1, y2), x1:max(x1, x2)]
    if crop.size == 0:
        return None, None
    plate, barcode = identify_from_crop(crop, mode, plate_detector=plate_detector, plate_conf=plate_conf)
    return plate, barcode


@celery_app.task(name="app.workers.tasks.process_camera_stream", bind=True)
def process_camera_stream(self, camera_id: int) -> None:
    """Consume a camera stream and generate events.

    This task reads frames from the sample video associated with the
    given camera. When a vehicle enters the ROI, an event is recorded
    and a notification is sent. For demonstration purposes the stream
    loops endlessly.

    Args:
        camera_id: Identifier of the camera to process.
    """
    db: Session = SessionLocal()
    try:
        if settings.DETECTION_BACKEND.lower() == "jetson":
            print("DETECTION_BACKEND=jetson stub active; implement DeepStream adapter.")
            return
        camera = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
        if not camera:
            return
        # Fetch ROI for the camera
        roi = (
            db.query(models.ROI)
            .filter(models.ROI.gate_id == camera.gate_id, models.ROI.camera_id == camera.id)
            .first()
        )
        if not roi:
            return
        # Build absolute path to sample video file; we assume mediamtx and backend
        # both mount /sample_media inside container
        video_path = os.getenv("SAMPLE_VIDEO_PATH", "/sample_media/sample.mp4")
        if not os.path.exists(video_path):
            m.inc_stream_error(camera_id)
            print(f"Sample video {video_path} not found")
            return
        detector = None
        plate_detector = None
        mat_estimator = None
        try:
            detector = YOLODetector(settings.YOLO_MODEL_PATH, conf_threshold=0.35, iou_threshold=0.45)
            print(f"[worker] Using YOLO model at {settings.YOLO_MODEL_PATH}")
        except Exception as exc:
            print(f"[worker] YOLO detector unavailable, using stub detector: {exc}")
        if str(settings.IDENT_MODE).upper() in ("ANPR", "BOTH"):
            try:
                plate_detector = PlateDetector(settings.PLATE_MODEL_PATH, conf_threshold=settings.PLATE_CONF, iou_threshold=0.45)
                print(f"[worker] Using plate model at {settings.PLATE_MODEL_PATH}")
            except Exception as exc:
                print(f"[worker] Plate detector unavailable, using heuristic: {exc}")
        # Material/load model if provided, else deterministic fallback
        if getattr(settings, "MATERIAL_MODEL_PATH", None) or getattr(settings, "LOAD_MODEL_PATH", None):
            mat_estimator = MaterialModelEstimator(
                material_model_path=getattr(settings, "MATERIAL_MODEL_PATH", None),
                load_model_path=getattr(settings, "LOAD_MODEL_PATH", None),
            )
            print(f"[worker] Using material/load models: {getattr(settings, 'MATERIAL_MODEL_PATH', None)}, {getattr(settings, 'LOAD_MODEL_PATH', None)}")
        else:
            mat_estimator = DeterministicEstimator()

        tracker = TrackManager(iou_threshold=0.35, max_age=20)
        inside_state: dict[int, bool] = {}
        last_pos: dict[int, tuple[float, float]] = {}

        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        backoff = 0.2
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(backoff)
                backoff = min(1.0, backoff + 0.1)
                continue
            backoff = 0.2
            frame_count += 1
            # Detect
            dets = []
            if detector:
                for d in detector.detect(frame):
                    dets.append({"bbox": d.bbox, "cls_name": d.cls_name, "conf": d.conf})
            else:
                for x, y, w, h, vehicle_type, conf in detect_vehicles(frame):
                    dets.append({
                        "bbox": (x, y, x + w, y + h),
                        "cls_name": vehicle_type.value if hasattr(vehicle_type, "value") else str(vehicle_type),
                        "conf": conf,
                    })

            tracks = tracker.update(dets)

            for t in tracks:
                x1, y1, x2, y2 = t.bbox
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2

                was_inside = inside_state.get(t.track_id, False)
                now_inside = point_inside_rect(cx, cy, roi.coordinates)
                prev_pos = last_pos.get(t.track_id)
                direction = models.EntryExit.entry
                if prev_pos:
                    dir_str = determine_entry_exit(prev_pos, (cx, cy), roi.coordinates)
                    direction = models.EntryExit.entry if dir_str == "ENTRY" else models.EntryExit.exit
                last_pos[t.track_id] = (cx, cy)
                inside_state[t.track_id] = now_inside

                # Trigger when the centroid crosses the ROI midline (more stable than simple enter)
                mid_cross = False
                if prev_pos:
                    _, prev_y = prev_pos
                    (x1_roi, y1_roi), (x2_roi, y2_roi) = roi.coordinates
                    mid_y = (y1_roi + y2_roi) / 2.0
                    mid_cross = (prev_y <= mid_y < cy) or (prev_y >= mid_y > cy)

                should_emit = mid_cross or ((not was_inside) and now_inside)
                if should_emit:
                    now = time.time()
                    key = (camera.id, t.track_id)
                    last_time = _last_event_time.get(key, 0)
                    # Debounce per track
                    if now - last_time < 2:
                        continue
                    _last_event_time[key] = now

                    # Save snapshot image (with rectangle overlay)
                    snapshot_dir = "/tmp/event_snapshots"
                    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
                    snapshot_filename = f"{uuid.uuid4()}.jpg"
                    snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
                    frame_copy = frame.copy()
                    cv2.rectangle(frame_copy, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.imwrite(snapshot_path, frame_copy)

                    # Upload to MinIO
                    minio_service = MinioService()
                    object_name = minio_service.upload_file(snapshot_path, snapshot_filename)
                    snapshot_url = minio_service.public_url(object_name)

                    # Map cls name to enum
                    vehicle_enum = None
                    cls_lower = t.cls_name.lower()
                    mapping = {
                        "truck": models.VehicleType.truck,
                        "dumper": models.VehicleType.dumper,
                        "car/4-wheeler": models.VehicleType.car,
                        "car": models.VehicleType.car,
                        "bike/2-wheeler": models.VehicleType.bike,
                        "bike": models.VehicleType.bike,
                        "tractor": models.VehicleType.tractor,
                        "trolley": models.VehicleType.tractor,
                    }
                    vehicle_enum = mapping.get(cls_lower, None)

                    plate, barcode = _identify_vehicle(frame, (x1, y1, x2, y2), settings.IDENT_MODE, plate_detector, settings.PLATE_CONF)

                    # Material/load estimation from crop
                    crop_for_load = frame[max(0, int(y1)):max(int(y1), int(y2)), max(0, int(x1)):max(int(x1), int(x2))]
                    est = mat_estimator.estimate(crop_for_load)
                    # Save load crop
                    load_crop_path = None
                    try:
                        load_crop_dir = "/tmp/load_crops"
                        Path(load_crop_dir).mkdir(parents=True, exist_ok=True)
                        load_crop_filename = f"load_{uuid.uuid4()}.jpg"
                        local_load_crop = os.path.join(load_crop_dir, load_crop_filename)
                        cv2.imwrite(local_load_crop, crop_for_load)
                        load_crop_obj = minio_service.upload_file(local_load_crop, load_crop_filename)
                        load_crop_path = minio_service.public_url(load_crop_obj)
                    except Exception as exc:
                        print(f"load crop save failed: {exc}")

                    event = models.Event(
                        gate_id=camera.gate_id,
                        camera_id=camera.id,
                        entry_exit=direction,
                        vehicle_type=vehicle_enum,
                        track_id=t.track_id,
                        confidence=t.conf,
                        timestamp=datetime.utcnow(),
                        snapshot_path=snapshot_url,
                        plate_number=plate,
                        barcode_value=barcode,
                        material_type=est.material_type,
                        material_confidence=est.material_confidence,
                        load_percentage=est.load_percentage,
                        load_label=est.load_label,
                        load_crop_path=load_crop_path,
                    )
                    db.add(event)
                    db.commit()
                    db.refresh(event)
                    m.inc_event(camera.gate_id, vehicle_enum.value if vehicle_enum else "Unknown", event.entry_exit.value)
                    send_notification.delay(event.id)
            time.sleep(0.05)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_notification")
def send_notification(event_id: int) -> None:
    """Send an email/SMS notification for a new event.

    In local mode this sends an email via MailHog and logs an SMS
    notification to stdout. The notification includes basic event
    metadata and a link to the snapshot image stored in MinIO.
    """
    db: Session = SessionLocal()
    try:
        event = db.query(models.Event).filter(models.Event.id == event_id).first()
        if not event:
            return
        camera = db.query(models.Camera).filter(models.Camera.id == event.camera_id).first()
        gate = db.query(models.Gate).filter(models.Gate.id == event.gate_id).first()
        # Apply per-gate rules
        rules = db.query(NotificationRule).filter(
            NotificationRule.gate_id == event.gate_id,
            NotificationRule.enabled == True,
            NotificationRule.min_confidence <= (event.confidence or 0),
        ).all()
        if not rules:
            return
        # filter by direction/vehicle type if set
        filtered_rules = []
        for r in rules:
            if r.directions:
                dirs = [d.strip().upper() for d in r.directions.split(",") if d.strip()]
                if event.entry_exit.value.upper() not in dirs:
                    continue
            if r.vehicle_types:
                vts = [v.strip().lower() for v in r.vehicle_types.split(",") if v.strip()]
                if event.vehicle_type and event.vehicle_type.value.lower() not in vts:
                    continue
            filtered_rules.append(r)
        rules = filtered_rules
        if not rules:
            return
        # Debounce per (gate, channel)
        now = time.time()
        rules_debounced = []
        for r in rules:
            key = (event.gate_id, r.channel.value)
            last = _last_notify_time.get(key, 0)
            if now - last < settings.NOTIFY_DEBOUNCE_SECONDS:
                continue
            _last_notify_time[key] = now
            rules_debounced.append(r)
        rules = rules_debounced
        if not rules:
            return
        # Compose email
        subject = f"Vehicle {event.entry_exit.value} at {gate.name}"
        body = (
            f"Time: {event.timestamp}\n"
            f"Gate: {gate.name}\n"
            f"Camera: {camera.name}\n"
            f"Type: {event.vehicle_type.value if event.vehicle_type else 'Unknown'}\n"
            f"Snapshot: {event.snapshot_path}\n"
        )
        # Send per-channel
        has_email = any(r.channel == NotificationChannel.email for r in rules)
        has_sms = any(r.channel == NotificationChannel.sms for r in rules)
        has_push = any(r.channel == NotificationChannel.push for r in rules)
        # Use recipients if provided
        recipients_email = []
        recipients_sms = []
        recipients_push = []
        for r in rules:
            if r.channel == NotificationChannel.email:
                recipients_email.extend(r.recipient_list())
            if r.channel == NotificationChannel.sms:
                recipients_sms.extend(r.recipient_list())
            if r.channel == NotificationChannel.push:
                recipients_push.extend(r.recipient_list())

        send_email(subject, body, recipients_email or None)
        send_sms(body, recipients_sms or None, has_sms)
        send_push(body, recipients_push or None, has_push)
    finally:
        db.close()


def send_email(subject: str, body: str, recipients: list[str] | None = None) -> None:
    """Send an email via SMTP using settings.

    For local development this will deliver to the MailHog service.
    """
    import smtplib
    from email.mime.text import MIMEText

    settings = get_settings()
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = ",".join(recipients) if recipients else "recipient@example.com"
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.send_message(msg)
        m.inc_notification("email", "success")
    except Exception as exc:
        print(f"Failed to send email: {exc}")
        m.inc_notification("email", "failure")


def send_sms(message: str, recipients: list[str] | None = None, enabled: bool = True) -> None:
    """Send SMS via Twilio if configured, otherwise log."""
    cfg = get_settings()
    dest_list = recipients or ([cfg.NOTIFY_SMS_TO] if cfg.NOTIFY_SMS_TO else [])
    if enabled and cfg.TWILIO_ACCOUNT_SID and cfg.TWILIO_AUTH_TOKEN and cfg.TWILIO_FROM_NUMBER and dest_list:
        try:
            from twilio.rest import Client
            client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
            for dest in dest_list:
                client.messages.create(
                    body=message,
                    from_=cfg.TWILIO_FROM_NUMBER,
                    to=dest,
                )
            m.inc_notification("sms", "success")
            return
        except Exception as exc:
            print(f"Twilio SMS failed: {exc}")
            m.inc_notification("sms", "failure")
    print(f"SMS notification (stub): {message}")
    m.inc_notification("sms", "stub")


def send_push(message: str, recipients: list[str] | None = None, enabled: bool = True) -> None:
    """Send push notifications via FCM legacy API if configured."""
    cfg = get_settings()
    if not enabled or not cfg.FCM_SERVER_KEY:
        m.inc_notification("push", "stub")
        return
    tokens = recipients or []
    if not tokens:
        m.inc_notification("push", "noop")
        return
    headers = {
        "Authorization": f"key={cfg.FCM_SERVER_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "registration_ids": tokens,
        "notification": {
            "title": "Vehicle event",
            "body": message[:200],
        },
        "data": {"type": "vehicle_event"},
    }
    try:
        resp = requests.post(cfg.FCM_ENDPOINT, json=payload, headers=headers, timeout=5)
        if resp.ok:
            m.inc_notification("push", "success")
        else:
            print(f"FCM push failed: {resp.status_code} {resp.text}")
            m.inc_notification("push", "failure")
    except Exception as exc:
        print(f"FCM push exception: {exc}")
        m.inc_notification("push", "failure")

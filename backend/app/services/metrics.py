"""In-memory metrics counters for local use."""

from collections import defaultdict
from typing import Dict, Tuple

events_total = defaultdict(int)  # key: (gate, vehicle_type, direction)
notifications_sent_total = defaultdict(int)  # key: (channel, status)
stream_errors_total = defaultdict(int)  # key: camera_id


def inc_event(gate: int, vehicle_type: str, direction: str):
    events_total[(gate, vehicle_type, direction)] += 1


def inc_notification(channel: str, status: str):
    notifications_sent_total[(channel, status)] += 1


def inc_stream_error(camera_id: int):
    stream_errors_total[camera_id] += 1

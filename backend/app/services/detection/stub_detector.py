"""Simple vehicle detector stub.

For the purposes of local testing without GPU acceleration, this
detector searches for a bright green rectangle in the frame. The
sample video provided in ``infra/sample_media`` contains a green
rectangle moving across the bottom of the frame. This stub returns a
single detection whenever the green rectangle is present. In a real
deployment this module can be replaced with an adapter around
YOLOv8/DeepStream/TensorRT for GPU inference on Jetson.
"""

from typing import List, Tuple

import cv2
import numpy as np

from app.db.models import VehicleType


def detect_vehicles(frame: np.ndarray) -> List[Tuple[int, int, int, int, VehicleType, float]]:
    """Detect vehicles in a frame.

    Args:
        frame: The input image in BGR format.
    Returns:
        A list of tuples containing (x, y, w, h, vehicle_type, confidence).
        The coordinates define the bounding box. For the stub always
        returns one detection for the green rectangle if present.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Threshold for green color of our sample rectangle
    mask = cv2.inRange(hsv, (40, 50, 50), (80, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < 500:  # ignore small blobs
            continue
        detections.append((x, y, w, h, VehicleType.truck, 0.9))
    return detections
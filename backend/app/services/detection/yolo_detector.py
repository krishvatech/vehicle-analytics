"""YOLO ONNX detector for vehicles with simple class remapping.

This uses OpenCV DNN with a YOLOv8 ONNX export. Expected output shape:
 (batch, num_dets, 4 + num_classes) with xywh format. If the model is
 structured differently, adapt parsing accordingly.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np

# COCO class indices for vehicles
COCO_CLASS_MAP = {
    2: "Car/4-wheeler",   # car
    3: "Bike/2-wheeler",  # motorcycle
    5: "Dumper",          # bus as dumper surrogate
    7: "Truck",           # truck
    1: "Bike/2-wheeler",  # bicycle
}


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x1,y1,x2,y2
    cls_name: str
    conf: float


class YOLODetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.4, iou_threshold: float = 0.45):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {self.model_path}")
        self.net = cv2.dnn.readNetFromONNX(str(self.model_path))
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def detect(self, frame) -> List[Detection]:
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        preds = self.net.forward()
        if isinstance(preds, list):
            preds = preds[0]
        preds = np.squeeze(preds)  # (num, 4+cls)

        bboxes = []
        scores = []
        class_ids = []
        for det in preds:
            if det.shape[0] < 6:
                continue
            cx, cy, bw, bh = det[:4]
            cls_scores = det[4:]
            cls_id = int(np.argmax(cls_scores))
            score = float(cls_scores[cls_id])
            if score < self.conf_threshold or cls_id not in COCO_CLASS_MAP:
                continue
            x1 = int((cx - bw / 2) * w / 640)
            y1 = int((cy - bh / 2) * h / 640)
            x2 = int((cx + bw / 2) * w / 640)
            y2 = int((cy + bh / 2) * h / 640)
            bboxes.append([x1, y1, x2, y2])
            scores.append(score)
            class_ids.append(cls_id)

        idxs = cv2.dnn.NMSBoxes(bboxes, scores, self.conf_threshold, self.iou_threshold)
        detections: List[Detection] = []
        if len(idxs) > 0:
            for i in idxs.flatten():
                cls_name = COCO_CLASS_MAP.get(class_ids[i], "Unknown")
                x1, y1, x2, y2 = bboxes[i]
                detections.append(Detection(bbox=(x1, y1, x2, y2), cls_name=cls_name, conf=float(scores[i])))
        return detections

"""YOLO ONNX plate detector."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np


@dataclass
class PlateDet:
    bbox: Tuple[int, int, int, int]  # x1,y1,x2,y2
    conf: float


class PlateDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.35, iou_threshold: float = 0.45):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Plate model not found at {self.model_path}")
        self.net = cv2.dnn.readNetFromONNX(str(self.model_path))
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def detect(self, frame) -> List[PlateDet]:
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        preds = self.net.forward()
        if isinstance(preds, list):
            preds = preds[0]
        preds = np.squeeze(preds)  # (num, 5+num_classes) assume single class

        bboxes = []
        scores = []
        for det in preds:
            if det.shape[0] < 5:
                continue
            cx, cy, bw, bh = det[:4]
            score = float(det[4])
            if score < self.conf_threshold:
                continue
            x1 = int((cx - bw / 2) * w / 640)
            y1 = int((cy - bh / 2) * h / 640)
            x2 = int((cx + bw / 2) * w / 640)
            y2 = int((cy + bh / 2) * h / 640)
            bboxes.append([x1, y1, x2, y2])
            scores.append(score)

        idxs = cv2.dnn.NMSBoxes(bboxes, scores, self.conf_threshold, self.iou_threshold)
        detections: List[PlateDet] = []
        if len(idxs) > 0:
            for i in idxs.flatten():
                x1, y1, x2, y2 = bboxes[i]
                detections.append(PlateDet(bbox=(x1, y1, x2, y2), conf=float(scores[i])))
        return detections

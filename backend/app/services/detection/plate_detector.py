"""
YOLOv8 ONNX plate detector using ONNX Runtime.
Supports outputs:
  - (1,C,N) or (1,N,C) where C=4+nc (usually nc=1)
  - (N,6) or (1,N,6) if exported with NMS: [x1,y1,x2,y2,score,class]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

try:
    import onnxruntime as ort
except Exception as e:  # pragma: no cover
    ort = None  # type: ignore


@dataclass
class PlateDet:
    bbox: Tuple[int, int, int, int]  # x1,y1,x2,y2
    conf: float


def _letterbox(img: np.ndarray, new_shape: int = 640, color=(114, 114, 114)):
    h, w = img.shape[:2]
    r = min(new_shape / h, new_shape / w)
    new_unpad = (int(round(w * r)), int(round(h * r)))
    dw = new_shape - new_unpad[0]
    dh = new_shape - new_unpad[1]
    dw /= 2
    dh /= 2

    if (w, h) != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img, r, (left, top)


def _iou_xyxy(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    a1 = (box[2] - box[0]) * (box[3] - box[1])
    a2 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (a1 + a2 - inter + 1e-9)


def _nms_xyxy(boxes: np.ndarray, scores: np.ndarray, iou_thr: float):
    idxs = scores.argsort()[::-1]
    keep = []
    while idxs.size > 0:
        i = idxs[0]
        keep.append(int(i))
        if idxs.size == 1:
            break
        ious = _iou_xyxy(boxes[i], boxes[idxs[1:]])
        idxs = idxs[1:][ious < iou_thr]
    return keep


class PlateDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.35, iou_threshold: float = 0.45, imgsz: int = 640):
        if ort is None:
            raise RuntimeError("onnxruntime is not installed. Add onnxruntime to requirements and rebuild images.")

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Plate model not found at {self.model_path}")

        self.conf_threshold = float(conf_threshold)
        self.iou_threshold = float(iou_threshold)
        self.imgsz = int(imgsz)

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(self.model_path), sess_options=so, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def detect(self, frame: np.ndarray) -> List[PlateDet]:
        h0, w0 = frame.shape[:2]

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img, r, (padw, padh) = _letterbox(img, new_shape=self.imgsz)

        x = img.astype(np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None, ...]

        outputs = self.session.run(None, {self.input_name: x})
        pred = np.asarray(outputs[0])

        # NMS-export style: (N,6) or (1,N,6)
        if pred.ndim == 3 and pred.shape[-1] == 6:
            pred = pred[0]
        if pred.ndim == 2 and pred.shape[1] == 6:
            boxes = pred[:, 0:4].astype(np.float32)
            scores = pred[:, 4].astype(np.float32)
        else:
            if pred.ndim == 3:
                pred = pred[0]
            pred = np.squeeze(pred)
            if pred.ndim == 2 and pred.shape[0] < pred.shape[1] and pred.shape[0] in (5, 6, 7, 8, 9, 10):
                pred = pred.T

            if pred.ndim != 2 or pred.shape[1] < 5:
                return []

            xywh = pred[:, 0:4].astype(np.float32)
            cls_probs = pred[:, 4:].astype(np.float32)
            # plate is single-class typically
            scores = cls_probs.max(axis=1)

            x_c, y_c, bw, bh = xywh[:, 0], xywh[:, 1], xywh[:, 2], xywh[:, 3]
            x1 = x_c - bw / 2
            y1 = y_c - bh / 2
            x2 = x_c + bw / 2
            y2 = y_c + bh / 2
            boxes = np.stack([x1, y1, x2, y2], axis=1)

        keep_mask = scores >= self.conf_threshold
        if keep_mask.sum() == 0:
            return []

        boxes = boxes[keep_mask]
        scores = scores[keep_mask]

        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - padw) / r
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - padh) / r

        boxes[:, 0] = np.clip(boxes[:, 0], 0, w0 - 1)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, w0 - 1)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, h0 - 1)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, h0 - 1)

        keep = _nms_xyxy(boxes, scores, self.iou_threshold)

        out: List[PlateDet] = []
        for i in keep:
            x1, y1, x2, y2 = boxes[i].astype(int).tolist()
            out.append(PlateDet(bbox=(x1, y1, x2, y2), conf=float(scores[i])))
        return out

"""Simple IOU-based tracker to keep persistent IDs across frames."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import itertools


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1e-6, area_a + area_b - inter)


@dataclass
class TrackState:
    track_id: int
    bbox: Tuple[int, int, int, int]
    cls_name: str
    conf: float
    age: int = 0


class TrackManager:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._next_id = itertools.count(1)
        self._tracks: Dict[int, TrackState] = {}

    def update(self, detections: List[dict]) -> List[TrackState]:
        # detections: list of dict with bbox, cls_name, conf
        assigned = set()
        new_tracks = {}

        # match existing to detections
        for tid, st in self._tracks.items():
            best_iou = 0.0
            best_idx = None
            for j, det in enumerate(detections):
                if j in assigned:
                    continue
                iou = _iou(st.bbox, det["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = j
            if best_idx is not None and best_iou >= self.iou_threshold:
                det = detections[best_idx]
                assigned.add(best_idx)
                new_tracks[tid] = TrackState(
                    track_id=tid,
                    bbox=det["bbox"],
                    cls_name=det["cls_name"],
                    conf=det["conf"],
                    age=0,
                )
            else:
                st.age += 1
                if st.age <= self.max_age:
                    new_tracks[tid] = st

        # new detections -> new tracks
        for j, det in enumerate(detections):
            if j in assigned:
                continue
            tid = next(self._next_id)
            new_tracks[tid] = TrackState(
                track_id=tid,
                bbox=det["bbox"],
                cls_name=det["cls_name"],
                conf=det["conf"],
                age=0,
            )

        self._tracks = new_tracks
        return list(self._tracks.values())

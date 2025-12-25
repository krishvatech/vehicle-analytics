from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import numpy as np
import cv2


@dataclass
class MaterialLoadEstimate:
    material_type: str
    material_confidence: float
    load_percentage: float
    load_label: str


class MaterialLoadEstimatorBase:
    def estimate(self, crop) -> MaterialLoadEstimate:
        raise NotImplementedError


class DeterministicEstimator(MaterialLoadEstimatorBase):
    """Deterministic, testable baseline using image stats."""

    def estimate(self, crop) -> MaterialLoadEstimate:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_val = float(np.mean(gray))
        std_val = float(np.std(gray))
        # Material based on std bucket
        if std_val < 20:
            mat = "sand"
        elif std_val < 40:
            mat = "soil"
        elif std_val < 60:
            mat = "stone"
        else:
            mat = "debris"
        conf = min(1.0, 0.5 + std_val / 100.0)
        pct = float(np.clip(mean_val / 255.0 * 100.0, 0, 100))
        if pct < 25:
            lbl = "Empty"
        elif pct < 50:
            lbl = "Partial"
        elif pct < 75:
            lbl = "Half"
        else:
            lbl = "Full"
        return MaterialLoadEstimate(material_type=mat, material_confidence=conf, load_percentage=pct, load_label=lbl)

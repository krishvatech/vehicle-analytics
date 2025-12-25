"""Placeholder material classification and load estimation.

These functions should be replaced with trained classifiers/regressors.
For now they produce deterministic pseudo-random outputs based on image hash,
so we can exercise the pipeline and UI end-to-end.
"""

from __future__ import annotations
from typing import Tuple
import cv2
import numpy as np

MATERIALS = ["sand", "soil", "stone", "debris"]


def classify_material(crop) -> Tuple[str, float]:
    # Deterministic pseudo-random pick based on mean pixel
    mean_val = float(np.mean(crop))
    idx = int(mean_val) % len(MATERIALS)
    conf = 0.55 + (mean_val % 45) / 100.0  # 0.55 - 1.0 range
    return MATERIALS[idx], min(1.0, conf)


def estimate_load(crop) -> Tuple[float, str]:
    # Use brightness as proxy for load % to keep deterministic
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    pct = float(np.clip(np.mean(gray) / 255.0 * 100.0, 0, 100))
    if pct < 25:
        level = "Empty"
    elif pct < 50:
        level = "Partial"
    elif pct < 75:
        level = "Half"
    else:
        level = "Full"
    return pct, level

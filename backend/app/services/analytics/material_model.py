"""Material classification and load estimation using optional ONNX models.

If model paths are provided (via settings), tries to run ONNXRuntime sessions.
Falls back to brightness-based heuristics when models are unavailable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    import onnxruntime as ort  # type: ignore
except Exception:
    ort = None  # Optional dependency


MATERIAL_LABELS = ["sand", "soil", "stone", "debris"]


@dataclass
class MaterialLoadEstimate:
    material_type: str
    material_confidence: float
    load_percentage: float
    load_label: str


class MaterialModelEstimator:
    """Wrapper around optional ONNX classifiers/regressors."""

    def __init__(
        self,
        material_model_path: Optional[str] = None,
        load_model_path: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ):
        self.labels = labels or MATERIAL_LABELS
        self.material_session = None
        self.load_session = None
        if ort and material_model_path and os.path.exists(material_model_path):
            try:
                self.material_session = ort.InferenceSession(material_model_path, providers=["CPUExecutionProvider"])
                # Heuristic: pick first input name
                self.material_input = self.material_session.get_inputs()[0].name
            except Exception as exc:
                print(f"Material model load failed ({material_model_path}): {exc}")
        if ort and load_model_path and os.path.exists(load_model_path):
            try:
                self.load_session = ort.InferenceSession(load_model_path, providers=["CPUExecutionProvider"])
                self.load_input = self.load_session.get_inputs()[0].name
            except Exception as exc:
                print(f"Load model load failed ({load_model_path}): {exc}")

    def _preprocess(self, img: np.ndarray, size: Tuple[int, int] = (224, 224)) -> np.ndarray:
        """Basic preprocess: BGR->RGB, resize, normalize to 0-1, NCHW float32."""
        resized = cv2.resize(img, size)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        arr = rgb.astype(np.float32) / 255.0
        chw = np.transpose(arr, (2, 0, 1))
        return np.expand_dims(chw, 0)  # (1,C,H,W)

    def _load_label(self, pct: float) -> str:
        if pct < 25:
            return "Empty"
        if pct < 50:
            return "Partial"
        if pct < 75:
            return "Half"
        return "Full"

    def estimate(self, crop: np.ndarray) -> MaterialLoadEstimate:
        """Run models if available; otherwise use heuristic brightness/std fallback."""
        material_type = "unknown"
        material_conf = 0.0
        load_pct = 0.0
        # Material classification
        if self.material_session is not None:
            try:
                inp = self._preprocess(crop)
                outputs = self.material_session.run(None, {self.material_input: inp})
                logits = outputs[0].squeeze()
                # softmax
                exp = np.exp(logits - np.max(logits))
                probs = exp / np.sum(exp)
                idx = int(np.argmax(probs))
                material_type = self.labels[idx] if idx < len(self.labels) else f"class_{idx}"
                material_conf = float(probs[idx])
            except Exception as exc:
                print(f"Material inference failed: {exc}")
        # Load estimation
        if self.load_session is not None:
            try:
                inp = self._preprocess(crop)
                outputs = self.load_session.run(None, {self.load_input: inp})
                load_val = float(np.squeeze(outputs[0]))
                # assume model outputs 0-1 or 0-100; clamp to 0-100
                if load_val <= 1.0:
                    load_pct = max(0.0, min(100.0, load_val * 100.0))
                else:
                    load_pct = max(0.0, min(100.0, load_val))
            except Exception as exc:
                print(f"Load inference failed: {exc}")
        # Fallbacks
        if material_conf == 0.0 or material_type == "unknown":
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            std_val = float(np.std(gray))
            if std_val < 20:
                material_type = "sand"
            elif std_val < 40:
                material_type = "soil"
            elif std_val < 60:
                material_type = "stone"
            else:
                material_type = "debris"
            material_conf = min(1.0, 0.5 + std_val / 100.0)
        if load_pct == 0.0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            load_pct = float(np.clip(np.mean(gray) / 255.0 * 100.0, 0, 100))
        load_label = self._load_label(load_pct)
        return MaterialLoadEstimate(
            material_type=material_type,
            material_confidence=material_conf,
            load_percentage=load_pct,
            load_label=load_label,
        )

"""Identification helpers for ANPR and barcode decoding.

This attempts lightweight OCR via pytesseract and barcode decode via pyzbar.
If native dependencies (tesseract binary, zbar) are missing, it will fallback
to returning None values.
"""

from __future__ import annotations
from typing import Optional, Tuple
import cv2
import numpy as np

try:
    import pytesseract
except Exception:
    pytesseract = None  # type: ignore

try:
    from pyzbar import pyzbar
except Exception:
    pyzbar = None  # type: ignore

try:
    from app.services.detection.plate_detector import PlateDetector
except Exception:
    PlateDetector = None  # type: ignore


def _clean_text(txt: str) -> str:
    txt = txt.strip()
    txt = txt.replace("\n", " ")
    return " ".join(txt.split())

def _find_plate_region(crop: np.ndarray) -> np.ndarray:
    """Heuristic plate region finder: looks for high-contrast, wide rectangles."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    # Edge emphasis
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(grad_x, grad_y)
    mag = cv2.convertScaleAbs(mag)
    _, th = cv2.threshold(mag, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((3, 15), np.uint8), iterations=2)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape[:2]
    best = None
    best_score = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw * ch < 0.001 * w * h:
            continue
        aspect = cw / max(1, ch)
        if aspect < 2 or aspect > 6:
            continue
        score = cw * ch
        if score > best_score:
            best_score = score
            best = (x, y, cw, ch)
    if best:
        x, y, cw, ch = best
        return crop[y : y + ch, x : x + cw]
    return crop


def _ocr_plate(crop: np.ndarray) -> Optional[str]:
    if pytesseract is None:
        return None
    plate_region = _find_plate_region(crop)
    gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    txt = pytesseract.image_to_string(th, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    txt = _clean_text(txt)
    return txt if txt else None


def _decode_barcode(crop: np.ndarray) -> Optional[str]:
    if pyzbar is None:
        return None
    barcodes = pyzbar.decode(crop)
    if not barcodes:
        return None
    return barcodes[0].data.decode("utf-8")


def identify_from_crop(crop: np.ndarray, mode: str, plate_detector: Optional["PlateDetector"] = None, plate_conf: float = 0.35) -> Tuple[Optional[str], Optional[str]]:
    """Return (plate, barcode) based on mode."""
    plate = None
    barcode = None
    mode_upper = mode.upper()
    if mode_upper in ("ANPR", "BOTH"):
        plate_region = crop
        if plate_detector is not None:
            try:
                dets = plate_detector.detect(crop)
                if dets:
                    best = max(dets, key=lambda d: d.conf)
                    if best.conf >= plate_conf:
                        x1, y1, x2, y2 = best.bbox
                        plate_region = crop[max(0, y1):max(y1, y2), max(0, x1):max(x1, x2)]
            except Exception:
                pass
        plate = _ocr_plate(plate_region)
    if mode_upper in ("BARCODE", "BOTH"):
        barcode = _decode_barcode(crop)
    return plate, barcode

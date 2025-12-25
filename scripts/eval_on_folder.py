"""
Offline evaluation helper.

Usage:
  python scripts/eval_on_folder.py --images ./samples --yolo /models/yolov8n.onnx --plate /models/plate.onnx

Outputs a CSV with detections and ANPR/barcode attempts so you can
hand-check accuracy and adjust thresholds.
"""

import argparse
import csv
from pathlib import Path

import cv2

from app.services.detection.yolo_detector import YOLODetector
from app.services.detection.plate_detector import PlateDetector
from app.services.detection.identification import identify_from_crop
from app.services.analytics.tracker import TrackManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, help="Folder of input images")
    parser.add_argument("--yolo", required=True, help="YOLO ONNX model path")
    parser.add_argument("--plate", help="Plate ONNX model path")
    parser.add_argument("--ident_mode", default="ANPR", help="ANPR|BARCODE|BOTH")
    parser.add_argument("--out", default="eval_results.csv", help="Output CSV")
    parser.add_argument("--conf", type=float, default=0.35, help="Vehicle conf threshold")
    parser.add_argument("--plate_conf", type=float, default=0.35, help="Plate conf threshold")
    args = parser.parse_args()

    yolo = YOLODetector(args.yolo, conf_threshold=args.conf, iou_threshold=0.45)
    plate = PlateDetector(args.plate, conf_threshold=args.plate_conf, iou_threshold=0.45) if args.plate else None
    tracker = TrackManager(iou_threshold=0.35, max_age=0)

    rows = []
    imgs = sorted(Path(args.images).glob("*.*"))
    for img_path in imgs:
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        dets = [{"bbox": d.bbox, "cls_name": d.cls_name, "conf": d.conf} for d in yolo.detect(frame)]
        tracks = tracker.update(dets)
        for t in tracks:
            x1, y1, x2, y2 = map(int, t.bbox)
            crop = frame[y1:y2, x1:x2]
            plate_txt, barcode_txt = identify_from_crop(crop, args.ident_mode, plate_detector=plate, plate_conf=args.plate_conf)
            rows.append({
                "image": img_path.name,
                "track_id": t.track_id,
                "cls_name": t.cls_name,
                "conf": t.conf,
                "bbox": f"{x1},{y1},{x2},{y2}",
                "plate": plate_txt or "",
                "barcode": barcode_txt or "",
            })

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "track_id", "cls_name", "conf", "bbox", "plate", "barcode"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} detections to {args.out}")


if __name__ == "__main__":
    main()

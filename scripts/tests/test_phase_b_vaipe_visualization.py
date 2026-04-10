"""Visualize Phase B matching on VAIPE using pill names and pill images.

This script uses:
- VAIPE train pill crops as reference images
- VAIPE test pill labels as ground-truth bboxes
- current ReferenceMatcher for matching

It saves annotated images with per-bbox tags so the user can inspect whether
the predicted pill name matches the VAIPE label.
"""

from __future__ import annotations

import argparse
import base64
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_b.s2_match.reference_matcher import ReferenceMatcher


TRAIN_IMG_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "train" / "pill" / "images"
TRAIN_LABEL_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "train" / "pill" / "labels"
TEST_IMG_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "test" / "pill" / "images"
TEST_LABEL_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "test" / "pill" / "labels"
ZERO_PIMA_CONFIG = ROOT / "Zero-PIMA" / "config.py"
PILL_INFO_CSV = ROOT / "Zero-PIMA" / "data" / "pill_information.csv"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "output" / "phase_b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refs-per-class", type=int, default=5)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--labels",
        default="",
        help="Comma-separated VAIPE label names to keep, e.g. 'Hapacol,Panadol-500mg'",
    )
    parser.add_argument(
        "--exact-label-set",
        action="store_true",
        help="Only keep test images whose unique labels exactly equal --labels",
    )
    return parser.parse_args()


def load_font(font_size: int):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    return ImageFont.load_default()


def load_label_map() -> dict[int, str]:
    spec = importlib.util.spec_from_file_location("zero_pima_config", ZERO_PIMA_CONFIG)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Zero-PIMA config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {value: key for key, value in module.ALL_PILL_LABELS.items()}


def load_pill_info() -> dict[str, dict[str, str]]:
    pill_info: dict[str, dict[str, str]] = {}
    with PILL_INFO_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pill_info[row["Pill"]] = {"color": row["Color"], "shape": row["Shape"]}
    return pill_info


def crop_to_b64(image, box: dict[str, Any]) -> str | None:
    x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    crop = image[y : y + h, x : x + w]
    if crop.size == 0:
        return None
    ok, buf = cv2.imencode(".png", crop)
    if not ok:
        return None
    return base64.b64encode(buf.tobytes()).decode("ascii")


def build_reference_profiles(
    id_to_name: dict[int, str],
    refs_per_class: int,
) -> dict[str, list[dict[str, str]]]:
    refs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for label_path in sorted(TRAIN_LABEL_DIR.glob("*.json")):
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        if not any(
            id_to_name.get(int(item["label"]))
            and len(refs[id_to_name[int(item["label"])]]) < refs_per_class
            for item in labels
        ):
            continue

        image = cv2.imread(str(TRAIN_IMG_DIR / f"{label_path.stem}.jpg"))
        if image is None:
            continue

        for item in labels:
            label_name = id_to_name.get(int(item["label"]))
            if not label_name or len(refs[label_name]) >= refs_per_class:
                continue
            encoded = crop_to_b64(image, item)
            if encoded:
                refs[label_name].append({"imageBase64": encoded})
    return refs


def build_metadata(label_name: str, pill_info: dict[str, dict[str, str]]) -> dict[str, Any]:
    info = pill_info.get(label_name, {})
    shape = info.get("shape", "")
    colors = [
        part.strip().lower()
        for part in info.get("color", "").replace(" and ", ",").split(",")
        if part.strip()
    ]
    return {
        "dosageForm": "Viên nang" if "capsule" in shape else "Viên nén",
        "visual": {"colors": colors, "shapeText": shape},
    }


def color_for_item(gt_name: str, pred_name: str | None, status: str) -> tuple[int, int, int]:
    if pred_name == gt_name and status == "assigned":
        return (22, 163, 74)
    if pred_name == gt_name:
        return (245, 158, 11)
    if status == "unknown":
        return (59, 130, 246)
    return (220, 38, 38)


def label_for_item(gt_name: str, det: dict[str, Any]) -> str:
    top_name = None
    suggestions = det.get("suggestions") or []
    if suggestions:
        top_name = suggestions[0].get("drugName")
    pred = det.get("assignedDrugName") or top_name or "?"
    status = det.get("status", "unknown")
    confidence = float(det.get("confidence", 0.0))
    return f"GT: {gt_name} | Pred: {pred} | {status} {confidence:.2f}"


def draw_annotations(image, rows: list[dict[str, Any]]):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img, "RGBA")
    font = load_font(max(18, image.shape[0] // 55))

    for row in rows:
        x1, y1, x2, y2 = row["bbox"]
        color = color_for_item(row["gtName"], row.get("predName"), row.get("status", "unknown"))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)

        label = row["label"]
        left, top, right, bottom = draw.textbbox((x1, y1), label, font=font)
        text_w = right - left
        text_h = bottom - top
        label_top = max(0, y1 - text_h - 10)
        label_box = [x1, label_top, x1 + text_w + 12, label_top + text_h + 8]
        draw.rectangle(label_box, fill=(*color, 225))
        draw.text((x1 + 6, label_top + 4), label, font=font, fill=(255, 255, 255, 255))

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def main() -> None:
    args = parse_args()
    selected_labels = {
        item.strip()
        for item in args.labels.split(",")
        if item.strip()
    }
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else DEFAULT_OUTPUT_ROOT / f"vaipe_visual_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    annotated_dir = output_dir / "annotated"
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)

    id_to_name = load_label_map()
    pill_info = load_pill_info()
    refs = build_reference_profiles(id_to_name, args.refs_per_class)
    matcher = ReferenceMatcher()

    summary_rows = []
    totals = Counter()

    test_files = []
    for label_path in sorted(TEST_LABEL_DIR.glob("*.json")):
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        names = {
            id_to_name.get(int(item["label"]))
            for item in labels
            if id_to_name.get(int(item["label"]))
        }
        if selected_labels:
            if not names:
                continue
            if args.exact_label_set:
                if names != selected_labels:
                    continue
            else:
                if not names.issubset(selected_labels):
                    continue
                if names.isdisjoint(selected_labels):
                    continue
        test_files.append(label_path)
        if args.limit > 0 and len(test_files) >= args.limit:
            break

    for label_path in test_files:
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        image_path = TEST_IMG_DIR / f"{label_path.stem}.jpg"
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        expected_counter = Counter()
        gt_names = []
        detections = []
        rows = []
        for item in labels:
            gt_name = id_to_name.get(int(item["label"]))
            if not gt_name:
                continue
            gt_names.append(gt_name)
            expected_counter[gt_name] += 1
            detections.append(
                {
                    "bbox": [
                        int(item["x"]),
                        int(item["y"]),
                        int(item["x"] + item["w"]),
                        int(item["y"] + item["h"]),
                    ],
                    "score": 1.0,
                    "label": 1,
                }
            )

        expected = [
            {
                "planId": name,
                "drugName": name,
                "expectedCount": count,
                "metadata": build_metadata(name, pill_info),
            }
            for name, count in expected_counter.items()
        ]
        reference_profiles = [
            {"planId": name, "drugName": name, "images": refs.get(name, [])}
            for name in expected_counter
            if refs.get(name)
        ]

        result = matcher.verify(
            image,
            detections,
            expected_medications=expected,
            reference_profiles=reference_profiles,
        )

        correct_top1 = 0
        correct_assigned = 0
        for gt_name, det in zip(gt_names, result["detections"]):
            top_name = det["suggestions"][0]["drugName"] if det.get("suggestions") else None
            if top_name == gt_name:
                correct_top1 += 1
                totals["top1Correct"] += 1
            if det.get("status") == "assigned" and det.get("assignedDrugName") == gt_name:
                correct_assigned += 1
                totals["assignedCorrect"] += 1

            totals["totalDetections"] += 1
            totals[f"status_{det.get('status', 'unknown')}"] += 1

            row = {
                "bbox": det.get("bbox"),
                "gtName": gt_name,
                "predName": det.get("assignedDrugName") or top_name,
                "status": det.get("status"),
                "confidence": det.get("confidence"),
                "label": label_for_item(gt_name, det),
                "suggestions": det.get("suggestions", []),
            }
            rows.append(row)

        annotated = draw_annotations(image, rows)
        annotated_path = annotated_dir / image_path.name
        cv2.imwrite(str(annotated_path), annotated)

        summary_rows.append(
            {
                "file": image_path.name,
                "annotatedPath": str(annotated_path),
                "pillCount": len(rows),
                "top1Correct": correct_top1,
                "assignedCorrect": correct_assigned,
                "detections": rows,
                "summary": result.get("summary", {}),
            }
        )

    total = totals["totalDetections"] or 1
    result_json = output_dir / "results.json"
    result_json.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_md = f"""# Phase B VAIPE Visual Review

## Cấu hình

- Ảnh reference mỗi class: `{args.refs_per_class}`
- Số ảnh test đã chạy: `{len(summary_rows)}`
- Dùng `GT bbox` của VAIPE để đánh giá matcher
- Bộ nhãn đang chạy: `{', '.join(sorted(selected_labels)) if selected_labels else 'Tất cả nhãn'}`

## Kết quả tổng quan

- Tổng viên thuốc: `{totals['totalDetections']}`
- Top-1 đúng: `{totals['top1Correct']}` / `{totals['totalDetections']}` (`{totals['top1Correct'] / total:.4f}`)
- Assigned đúng: `{totals['assignedCorrect']}` / `{totals['totalDetections']}` (`{totals['assignedCorrect'] / total:.4f}`)
- Assigned: `{totals['status_assigned']}`
- Uncertain: `{totals['status_uncertain']}`
- Unknown: `{totals['status_unknown']}`
- Extra: `{totals['status_extra']}`

## File kết quả

- Ảnh annotated: `{annotated_dir}`
- JSON chi tiết: `{result_json}`
"""
    (output_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    print(
        json.dumps(
            {
                "outputDir": str(output_dir),
                "annotatedDir": str(annotated_dir),
                "summary": str(output_dir / "summary.md"),
                "resultJson": str(result_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""Benchmark Phase B matcher on VAIPE pill dataset using GT pill boxes.

This script evaluates the current Phase B reference matcher against the
VAIPE train/test pill split.

It uses:
- train pill crops as reference images
- test pill ground-truth boxes as detections
- Zero-PIMA pill_information.csv as metadata hints

The benchmark isolates matching quality. It does not measure detector quality.
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

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_b.s2_match.reference_matcher import ReferenceMatcher


TRAIN_IMG_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "train" / "pill" / "images"
TRAIN_LABEL_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "train" / "pill" / "labels"
TEST_IMG_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "test" / "pill" / "images"
TEST_LABEL_DIR = ROOT / "archive" / "VAIPE_Full" / "content" / "dataset" / "test" / "pill" / "labels"
PILL_INFO_CSV = ROOT / "Zero-PIMA" / "data" / "pill_information.csv"
ZERO_PIMA_CONFIG = ROOT / "Zero-PIMA" / "config.py"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "output" / "phase_b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refs-per-class", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of test files; 0 means all")
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


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


def crop_to_b64(image, box: dict) -> str | None:
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
        needed = False
        for item in labels:
            label_name = id_to_name.get(int(item["label"]))
            if label_name and len(refs[label_name]) < refs_per_class:
                needed = True
                break
        if not needed:
            continue

        image_path = TRAIN_IMG_DIR / f"{label_path.stem}.jpg"
        image = cv2.imread(str(image_path))
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


def build_metadata(label_name: str, pill_info: dict[str, dict[str, str]]) -> dict:
    info = pill_info.get(label_name, {})
    shape = info.get("shape", "")
    color_raw = info.get("color", "")
    colors = [
        part.strip().lower()
        for part in color_raw.replace(" and ", ",").split(",")
        if part.strip()
    ]
    dosage = "Viên nang" if "capsule" in shape else "Viên nén"
    return {
        "dosageForm": dosage,
        "visual": {
            "colors": colors,
            "shapeText": shape,
        },
    }


def evaluate(
    matcher: ReferenceMatcher,
    id_to_name: dict[int, str],
    pill_info: dict[str, dict[str, str]],
    reference_profiles: dict[str, list[dict[str, str]]],
    limit: int,
) -> dict:
    counts = Counter()
    wrong_examples = []
    per_class = defaultdict(lambda: Counter())

    test_files = sorted(TEST_LABEL_DIR.glob("*.json"))
    if limit > 0:
        test_files = test_files[:limit]

    seen_classes = set()
    for label_path in test_files:
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        image_path = TEST_IMG_DIR / f"{label_path.stem}.jpg"
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        detections = []
        expected_counter = Counter()
        gt_names = []
        for item in labels:
            label_name = id_to_name.get(int(item["label"]))
            if not label_name:
                continue
            seen_classes.add(label_name)
            gt_names.append(label_name)
            expected_counter[label_name] += 1
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
                "planId": label_name,
                "drugName": label_name,
                "expectedCount": count,
                "metadata": build_metadata(label_name, pill_info),
            }
            for label_name, count in expected_counter.items()
        ]
        profiles = [
            {
                "planId": label_name,
                "drugName": label_name,
                "images": reference_profiles.get(label_name, []),
            }
            for label_name in expected_counter
            if reference_profiles.get(label_name)
        ]

        result = matcher.verify(
            image,
            detections,
            expected_medications=expected,
            reference_profiles=profiles,
        )

        counts["images"] += 1
        counts["image_all_top1"] += int(True)
        for gt_name, det in zip(gt_names, result["detections"]):
            counts["totalDetections"] += 1
            per_class[gt_name]["total"] += 1
            top1 = det["suggestions"][0]["drugName"] if det.get("suggestions") else None
            if top1 == gt_name:
                counts["top1Correct"] += 1
                per_class[gt_name]["top1Correct"] += 1
            else:
                counts["image_all_top1"] -= 1

            status = det.get("status") or "unknown"
            counts[f"status_{status}"] += 1

            if status == "assigned":
                counts["assigned"] += 1
                if det.get("assignedDrugName") == gt_name:
                    counts["assignedCorrect"] += 1
                    per_class[gt_name]["assignedCorrect"] += 1
                else:
                    wrong_examples.append(
                        {
                            "file": image_path.name,
                            "gt": gt_name,
                            "pred": det.get("assignedDrugName"),
                            "status": status,
                            "confidence": det.get("confidence"),
                            "suggestions": det.get("suggestions", []),
                        }
                    )
            elif top1 != gt_name:
                wrong_examples.append(
                    {
                        "file": image_path.name,
                        "gt": gt_name,
                        "pred": top1,
                        "status": status,
                        "confidence": det.get("confidence"),
                        "suggestions": det.get("suggestions", []),
                    }
                )

    missing_reference_labels = sorted(label for label in seen_classes if label not in reference_profiles)
    per_class_rows = []
    for label_name, data in per_class.items():
        total = data["total"]
        per_class_rows.append(
            {
                "label": label_name,
                "total": total,
                "top1Correct": data["top1Correct"],
                "top1Accuracy": round(data["top1Correct"] / total, 4) if total else 0.0,
                "assignedCorrect": data["assignedCorrect"],
            }
        )
    per_class_rows.sort(key=lambda item: (item["top1Accuracy"], item["total"]))

    total = counts["totalDetections"] or 1
    assigned = counts["assigned"] or 1
    return {
        "images": counts["images"],
        "totalDetections": counts["totalDetections"],
        "referenceClasses": len(reference_profiles),
        "seenClasses": len(seen_classes),
        "missingReferenceLabels": missing_reference_labels,
        "top1Correct": counts["top1Correct"],
        "top1Accuracy": round(counts["top1Correct"] / total, 4),
        "assigned": counts["assigned"],
        "assignedCorrect": counts["assignedCorrect"],
        "assignedRate": round(counts["assigned"] / total, 4),
        "assignedPrecision": round(counts["assignedCorrect"] / assigned, 4) if counts["assigned"] else 0.0,
        "assignedCorrectOverTotal": round(counts["assignedCorrect"] / total, 4),
        "uncertain": counts["status_uncertain"],
        "unknown": counts["status_unknown"],
        "extra": counts["status_extra"],
        "imageAllTop1": counts["image_all_top1"],
        "imageAllTop1Accuracy": round(counts["image_all_top1"] / max(1, counts["images"]), 4),
        "worstClasses": per_class_rows[:20],
        "sampleErrors": wrong_examples[:50],
    }


def main() -> None:
    args = parse_args()
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = DEFAULT_OUTPUT_ROOT / f"vaipe_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    id_to_name = load_label_map()
    pill_info = load_pill_info()
    reference_profiles = build_reference_profiles(id_to_name, args.refs_per_class)

    matcher = ReferenceMatcher()
    summary = evaluate(
        matcher,
        id_to_name,
        pill_info,
        reference_profiles,
        args.limit,
    )

    reference_stats = {
        "refsPerClass": args.refs_per_class,
        "referenceClasses": len(reference_profiles),
        "referenceLabelCounts": {
            label_name: len(images)
            for label_name, images in sorted(reference_profiles.items())
        },
    }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "reference_stats.json").write_text(
        json.dumps(reference_stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_md = f"""# VAIPE Phase B Benchmark

## Cấu hình

- Reference mỗi class: `{args.refs_per_class}`
- Số file test: `{summary['images']}`
- Kiểu benchmark: `GT boxes -> current ReferenceMatcher`
- Ghi chú: benchmark này đo **matching quality**, chưa đo detector quality.

## Kết quả chính

- Tổng detections GT: `{summary['totalDetections']}`
- Số class có reference từ train: `{summary['referenceClasses']}` / class xuất hiện trong test: `{summary['seenClasses']}`
- Top-1 đúng: `{summary['top1Correct']}` / `{summary['totalDetections']}` (`{summary['top1Accuracy']}`)
- Assigned: `{summary['assigned']}` / `{summary['totalDetections']}` (`{summary['assignedRate']}`)
- Assigned đúng: `{summary['assignedCorrect']}` / `{summary['totalDetections']}` (`{summary['assignedCorrectOverTotal']}`)
- Assigned precision: `{summary['assignedPrecision']}`
- Uncertain: `{summary['uncertain']}`
- Unknown: `{summary['unknown']}`
- Extra: `{summary['extra']}`
- Ảnh mà toàn bộ pills có top-1 đúng: `{summary['imageAllTop1']}` / `{summary['images']}` (`{summary['imageAllTop1Accuracy']}`)

## Ghi chú nhanh

- Nếu xem matcher như `gợi ý top-1`, đây là mức chính xác thô.
- Nếu xem matcher như `auto-assign` theo threshold hiện tại, hãy nhìn `assignedRate` và `assignedPrecision`.
- Những class tệ nhất được lưu trong `summary.json`.
"""
    (output_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    print(json.dumps({
        "outputDir": str(output_dir),
        "summaryJson": str(output_dir / 'summary.json'),
        "summaryMd": str(output_dir / 'summary.md'),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

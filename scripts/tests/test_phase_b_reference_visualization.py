"""Generate annotated Phase B review images from reference matching.

Usage:
    ./venv/bin/python scripts/tests/test_phase_b_reference_visualization.py

Optional:
    ./venv/bin/python scripts/tests/test_phase_b_reference_visualization.py \
        --reference-dir "data/input/Phase_B /ảnh từng viên thuốc" \
        --verify-dir "data/input/Phase_B /verify" \
        --output-dir "data/output/phase_b/reference_review_manual"
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import httpx
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_b.s1_pill_detect.pill_detector import PillDetector
from core.phase_b.s2_match.reference_matcher import ReferenceMatcher
from server.services.drug_service import DrugService

DEFAULT_REFERENCE_DIR = ROOT / "data" / "input" / "Phase_B " / "ảnh từng viên thuốc"
DEFAULT_VERIFY_DIR = ROOT / "data" / "input" / "Phase_B " / "verify"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "output" / "phase_b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", default=str(DEFAULT_REFERENCE_DIR))
    parser.add_argument("--verify-dir", default=str(DEFAULT_VERIFY_DIR))
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--reference-names",
        default="",
        help="Comma-separated names mapped to flat reference files in sorted order",
    )
    parser.add_argument(
        "--expected-names",
        default="",
        help="Comma-separated expected drug names when there are no prior reference pill images",
    )
    parser.add_argument(
        "--metadata-reference-only",
        action="store_true",
        help="Build temporary references from metadata/web images instead of local pill images",
    )
    parser.add_argument("--max-metadata-images", type=int, default=3)
    parser.add_argument(
        "--tag-name-only",
        action="store_true",
        help="Only draw the suggested drug name on each bbox tag",
    )
    parser.add_argument("--score-thresh", type=float, default=0.3)
    parser.add_argument("--assigned-threshold", type=float, default=0.8)
    parser.add_argument("--uncertain-threshold", type=float, default=0.62)
    parser.add_argument("--no-crop-reference", action="store_true")
    return parser.parse_args()


def friendly_name_from_stem(stem: str) -> str:
    stem = stem.strip().lower()
    if stem.startswith("thuoc_"):
        suffix = stem.split("thuoc_", 1)[1].replace("_", " ").strip()
        return f"Thuốc {suffix}".strip()
    return stem.replace("_", " ").title()


def collect_reference_items(
    reference_dir: Path,
    custom_names: list[str] | None = None,
) -> list[tuple[str, Path]]:
    """Collect `(label_name, image_path)` from flat files or labeled subfolders."""
    supported = {".png", ".jpg", ".jpeg", ".webp"}
    items: list[tuple[str, Path]] = []

    direct_images = sorted(
        p for p in reference_dir.iterdir() if p.is_file() and p.suffix.lower() in supported
    )
    if custom_names:
        if len(custom_names) != len(direct_images):
            raise ValueError(
                "Number of --reference-names must equal number of flat reference images"
            )
        for image_path, custom_name in zip(direct_images, custom_names):
            items.append((custom_name.strip(), image_path))
    else:
        for image_path in direct_images:
            items.append((friendly_name_from_stem(image_path.stem), image_path))

    subdirs = sorted(p for p in reference_dir.iterdir() if p.is_dir())
    for folder in subdirs:
        label_name = friendly_name_from_stem(folder.name)
        for image_path in sorted(folder.rglob("*")):
            if image_path.is_file() and image_path.suffix.lower() in supported:
                items.append((label_name, image_path))

    return items


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


def build_reference_profiles(
    detector: PillDetector,
    reference_dir: Path,
    cropped_dir: Path,
    use_cropped: bool,
    custom_names: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected = []
    profiles = []
    reference_items = collect_reference_items(reference_dir, custom_names=custom_names)
    if not reference_items:
        raise FileNotFoundError(f"No reference images found in {reference_dir}")

    grouped: dict[str, list[Path]] = {}
    for drug_name, ref_path in reference_items:
        grouped.setdefault(drug_name, []).append(ref_path)

    for idx, (drug_name, ref_paths) in enumerate(sorted(grouped.items()), start=1):
        plan_id = f"ref-{idx}"
        expected.append({"planId": plan_id, "drugName": drug_name, "pillsPerDose": 1})
        images_payload = []

        for image_index, ref_path in enumerate(ref_paths, start=1):
            if use_cropped:
                image = cv2.imread(str(ref_path))
                detections = detector.detect(image)
                if detections:
                    x1, y1, x2, y2 = detections[0]["bbox"]
                    crop = image[y1:y2, x1:x2]
                else:
                    crop = image
                crop_name = f"{plan_id}_{image_index}_{ref_path.stem}.png"
                crop_path = cropped_dir / crop_name
                cv2.imwrite(str(crop_path), crop)
                ok, buf = cv2.imencode(".png", crop)
                if not ok:
                    raise RuntimeError(f"Cannot encode reference crop for {ref_path.name}")
                images_payload.append(
                    {"imageBase64": base64.b64encode(buf.tobytes()).decode("ascii")}
                )
            else:
                images_payload.append({"imagePath": str(ref_path)})

        profiles.append(
            {
                "planId": plan_id,
                "drugName": drug_name,
                "images": images_payload,
            }
        )

    return expected, profiles


async def enrich_expected_metadata(expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    service = DrugService()
    enriched = []
    for item in expected:
        item_copy = dict(item)
        try:
            item_copy["metadata"] = await service.enrich_metadata(item_copy["drugName"])
        except Exception:
            item_copy["metadata"] = {}
        enriched.append(item_copy)
    return enriched


def _query_candidates(name: str) -> list[str]:
    candidates = []
    inside = re.findall(r"\((.*?)\)", name)
    outside = re.sub(r"\(.*?\)", "", name).strip()
    for value in inside + [outside, name]:
        value = re.sub(r"\s+", " ", value).strip(" -")
        if value and value not in candidates:
            candidates.append(value)
    return candidates


async def build_metadata_reference_profiles(
    expected_names: list[str],
    metadata_dir: Path,
    max_images: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    service = DrugService()
    expected: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for idx, original_name in enumerate(expected_names, start=1):
            metadata = {}
            for query_name in _query_candidates(original_name):
                try:
                    metadata = await service.enrich_metadata(query_name)
                except Exception:
                    metadata = {}
                image_candidates = metadata.get("images") or []
                if metadata or image_candidates:
                    break

            expected_item = {
                "planId": f"meta-{idx}",
                "drugName": original_name,
                "pillsPerDose": 1,
                "metadata": metadata or {},
            }
            expected.append(expected_item)

            image_payloads = []
            image_urls = []
            for item in (metadata.get("images") or []):
                url = item.get("url") if isinstance(item, dict) else None
                if url and url not in image_urls:
                    image_urls.append(url)
                if len(image_urls) >= max_images:
                    break

            for image_index, url in enumerate(image_urls, start=1):
                try:
                    resp = await client.get(url)
                except Exception:
                    continue
                if resp.status_code != 200:
                    continue
                ext = ".jpg"
                content_type = resp.headers.get("content-type", "")
                if "png" in content_type:
                    ext = ".png"
                image_path = metadata_dir / f"meta_{idx}_{image_index}{ext}"
                image_path.write_bytes(resp.content)
                image_payloads.append({"imagePath": str(image_path)})

            profiles.append(
                {
                    "planId": expected_item["planId"],
                    "drugName": expected_item["drugName"],
                    "images": image_payloads,
                }
            )

    return expected, profiles


def label_for_detection(det: dict[str, Any], *, name_only: bool = False) -> str:
    status = det.get("status")
    confidence = float(det.get("confidence", 0.0))
    assigned = det.get("assignedDrugName")
    suggestions = det.get("suggestions") or []
    top_name = suggestions[0]["drugName"] if suggestions else None

    if name_only:
        return assigned or top_name or "Không rõ"

    if status == "assigned":
        return f"Đã gán: {assigned} ({confidence:.2f})"
    if status == "uncertain":
        if top_name:
            return f"Không chắc: {top_name} ({confidence:.2f})"
        return f"Không chắc ({confidence:.2f})"
    if status == "extra":
        if assigned:
            return f"Viên dư: {assigned}"
        return "Viên dư"
    if top_name:
        return f"Chưa rõ, gợi ý: {top_name} ({confidence:.2f})"
    return "Viên lạ / chưa rõ"


def color_for_status(status: str) -> tuple[int, int, int]:
    if status == "assigned":
        return (22, 163, 74)
    if status == "uncertain":
        return (245, 158, 11)
    if status == "extra":
        return (220, 38, 38)
    return (59, 130, 246)


def _intersects(a: list[int], b: list[int]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _place_label_box(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    text_w: int,
    text_h: int,
    img_w: int,
    img_h: int,
    occupied: list[list[int]],
) -> list[int]:
    candidates = [
        [x1, max(0, y1 - text_h - 12), x1 + text_w + 12, max(0, y1 - text_h - 12) + text_h + 8],
        [x1, min(img_h - text_h - 8, y2 + 6), x1 + text_w + 12, min(img_h - text_h - 8, y2 + 6) + text_h + 8],
        [max(0, x2 - text_w - 12), max(0, y1 - text_h - 12), max(0, x2 - text_w - 12) + text_w + 12, max(0, y1 - text_h - 12) + text_h + 8],
    ]
    for box in candidates:
        box[2] = min(img_w - 1, box[2])
        box[3] = min(img_h - 1, box[3])
        if not any(_intersects(box, used) for used in occupied):
            occupied.append(box)
            return box

    for shift in range(0, 220, text_h + 10):
        top = min(max(0, y2 + 6 + shift), img_h - text_h - 8)
        box = [x1, top, min(img_w - 1, x1 + text_w + 12), top + text_h + 8]
        if not any(_intersects(box, used) for used in occupied):
            occupied.append(box)
            return box

    box = [x1, max(0, y1 - text_h - 12), min(img_w - 1, x1 + text_w + 12), max(0, y1 - text_h - 12) + text_h + 8]
    occupied.append(box)
    return box


def draw_annotations(image, detections: list[dict[str, Any]], *, name_only: bool = False):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img, "RGBA")
    font = load_font(max(16, image.shape[0] // 40))
    occupied: list[list[int]] = []
    img_h, img_w = image.shape[:2]

    for det in detections:
        bbox = det.get("bbox") or [0, 0, 0, 0]
        if len(bbox) != 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in bbox]
        color = color_for_status(str(det.get("status", "unknown")))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)

        label = label_for_detection(det, name_only=name_only)
        left, top, right, bottom = draw.textbbox((x1, y1), label, font=font)
        text_w = right - left
        text_h = bottom - top
        label_box = _place_label_box(x1, y1, x2, y2, text_w, text_h, img_w, img_h, occupied)
        draw.rectangle(label_box, fill=(*color, 220))
        draw.text((label_box[0] + 6, label_box[1] + 4), label, font=font, fill=(255, 255, 255, 255))

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def summarize_item(item: dict[str, Any]) -> str:
    summary = item.get("summary", {})
    return (
        f"- {item['file']}: detect={item['detections']}, assigned={summary.get('assigned', 0)}, "
        f"uncertain={summary.get('uncertain', 0)}, unknown={summary.get('unknown', 0)}, "
        f"extra={summary.get('extra', 0)}, missing={summary.get('missingExpected', 0)}"
    )


def main() -> None:
    args = parse_args()
    reference_dir = Path(args.reference_dir)
    verify_dir = Path(args.verify_dir)
    custom_names = [item.strip() for item in args.reference_names.split(",") if item.strip()]
    expected_names = [item.strip() for item in args.expected_names.split(",") if item.strip()]

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = DEFAULT_OUTPUT_ROOT / f"reference_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    annotated_dir = output_dir / "annotated"
    cropped_dir = output_dir / "cropped_references"
    metadata_dir = output_dir / "metadata_references"
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    cropped_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    detector = PillDetector(score_thresh=args.score_thresh)
    matcher = ReferenceMatcher(
        assigned_threshold=args.assigned_threshold,
        uncertain_threshold=args.uncertain_threshold,
    )

    if args.metadata_reference_only:
        if not expected_names:
            raise ValueError("--expected-names is required when --metadata-reference-only is used")
        expected, reference_profiles = asyncio.run(
            build_metadata_reference_profiles(
                expected_names,
                metadata_dir,
                args.max_metadata_images,
            )
        )
        expected = asyncio.run(enrich_expected_metadata(expected))
    else:
        expected, reference_profiles = build_reference_profiles(
            detector,
            reference_dir,
            cropped_dir,
            use_cropped=not args.no_crop_reference,
            custom_names=custom_names or None,
        )
        expected = asyncio.run(enrich_expected_metadata(expected))

    verify_files = sorted(
        p for p in verify_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not verify_files:
        raise FileNotFoundError(f"No verify images found in {verify_dir}")

    results = []
    for verify_path in verify_files:
        image = cv2.imread(str(verify_path))
        detections = detector.detect(image)
        verify_result = matcher.verify(
            image,
            detections,
            expected_medications=expected,
            reference_profiles=reference_profiles,
        )

        annotated = draw_annotations(
            image,
            verify_result.get("detections", []),
            name_only=args.tag_name_only,
        )
        annotated_path = annotated_dir / verify_path.name
        cv2.imwrite(str(annotated_path), annotated)

        item = {
            "file": verify_path.name,
            "annotatedPath": str(annotated_path),
            "detections": len(detections),
            "summary": verify_result.get("summary", {}),
            "referenceCoverage": verify_result.get("referenceCoverage", {}),
            "detectionsDetail": [
                {
                    "idx": det.get("detectionIdx"),
                    "bbox": det.get("bbox"),
                    "status": det.get("status"),
                    "assignedDrugName": det.get("assignedDrugName"),
                    "confidence": det.get("confidence"),
                    "suggestions": det.get("suggestions", []),
                    "label": label_for_detection(det, name_only=args.tag_name_only),
                }
                for det in verify_result.get("detections", [])
            ],
        }
        results.append(item)

    result_path = output_dir / "annotated_results.json"
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# Phase B Annotated Review",
        "",
        "## Đầu vào",
        "",
        f"- Thư mục ảnh mẫu: `{reference_dir}`",
        f"- Thư mục verify: `{verify_dir}`",
        f"- Chế độ ảnh mẫu: `{'cropped_reference' if not args.no_crop_reference else 'raw_reference'}`",
        f"- Nhãn thuốc dùng để match: `{', '.join(item['drugName'] for item in expected)}`",
        f"- Số ảnh metadata tải được: `{sum(len(profile.get('images', [])) for profile in reference_profiles)}`",
        "",
        "## Kết quả tổng quan",
        "",
    ]
    summary_lines.extend(summarize_item(item) for item in results)
    summary_lines.extend(
        [
            "",
            "## File kết quả",
            "",
            f"- JSON chi tiết: `{result_path}`",
            f"- Thư mục ảnh annotated: `{annotated_dir}`",
        ]
    )
    (output_dir / "annotated_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(json.dumps({
        "outputDir": str(output_dir),
        "annotatedDir": str(annotated_dir),
        "resultJson": str(result_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import numpy as np

    main()

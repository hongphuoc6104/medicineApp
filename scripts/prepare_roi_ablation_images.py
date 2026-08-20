"""
scripts/prepare_roi_ablation_images.py — Generates C0 (Full), C1 (Doc Crop), C2 (Medication ROI) image sets
for on-device ML Kit OCR ablation testing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrepareRoiImages")


def generate_roi_samples(
    image_dir: Path,
    label_dir: Path,
    output_dir: Path,
    num_samples: int = 30,
):
    """Generate C0, C1, C2 crops for ablation experiments."""
    output_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(list(image_dir.glob("*.png")))[:num_samples]
    manifest = []

    logger.info(f"Generating C0, C1, C2 crops for {len(image_files)} sample prescriptions...")

    for img_file in image_files:
        image_id = img_file.stem
        label_file = label_dir / f"{image_id}.json"

        if not label_file.exists():
            logger.warning(f"Label file not found for {image_id}, skipping.")
            continue

        with open(label_file, "r", encoding="utf-8") as f:
            labels = json.load(f)

        orig_img = Image.open(img_file).convert("RGB")
        w, h = orig_img.size

        # 1. C0: Full raw image
        c0_filename = f"c0_{image_id}.png"
        orig_img.save(output_dir / c0_filename)

        # 2. C1: Document page crop (all text elements + 3% margin)
        all_boxes = [item["box"] for item in labels if "box" in item and len(item["box"]) == 4]
        if all_boxes:
            c1_xmin = max(0, min(b[0] for b in all_boxes) - int(w * 0.03))
            c1_ymin = max(0, min(b[1] for b in all_boxes) - int(h * 0.03))
            c1_xmax = min(w, max(b[2] for b in all_boxes) + int(w * 0.03))
            c1_ymax = min(h, max(b[3] for b in all_boxes) + int(h * 0.03))
        else:
            c1_xmin, c1_ymin, c1_xmax, c1_ymax = 0, 0, w, h

        c1_crop = orig_img.crop((c1_xmin, c1_ymin, c1_xmax, c1_ymax))
        c1_filename = f"c1_{image_id}.png"
        c1_crop.save(output_dir / c1_filename)

        # 3. C2: Medication table ROI (drugname, quantity, usage + 4% margin)
        med_boxes = [
            item["box"]
            for item in labels
            if item.get("label") in ("drugname", "quantity", "usage") and "box" in item and len(item["box"]) == 4
        ]
        if not med_boxes:
            med_boxes = all_boxes

        if med_boxes:
            c2_xmin = max(0, min(b[0] for b in med_boxes) - int(w * 0.04))
            c2_ymin = max(0, min(b[1] for b in med_boxes) - int(h * 0.04))
            c2_xmax = min(w, max(b[2] for b in med_boxes) + int(w * 0.04))
            c2_ymax = min(h, max(b[3] for b in med_boxes) + int(h * 0.04))
        else:
            c2_xmin, c2_ymin, c2_xmax, c2_ymax = 0, 0, w, h

        c2_crop = orig_img.crop((c2_xmin, c2_ymin, c2_xmax, c2_ymax))
        c2_filename = f"c2_{image_id}.png"
        c2_crop.save(output_dir / c2_filename)

        # Record gold drugs
        gold_drugs = [
            {
                "id": item.get("id"),
                "text": item.get("text", "").strip(),
                "box": item.get("box"),
            }
            for item in labels
            if item.get("label") == "drugname"
        ]

        manifest.append({
            "image_id": image_id,
            "orig_width": w,
            "orig_height": h,
            "c0_file": c0_filename,
            "c1_file": c1_filename,
            "c2_file": c2_filename,
            "c1_box": [c1_xmin, c1_ymin, c1_xmax, c1_ymax],
            "c2_box": [c2_xmin, c2_ymin, c2_xmax, c2_ymax],
            "gold_drugs": gold_drugs,
        })

    manifest_path = output_dir / "roi_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Generated {len(manifest)} sets of (C0, C1, C2) crops in {output_dir.resolve()}.")
    logger.info(f"Manifest written to {manifest_path.resolve()}.")


if __name__ == "__main__":
    img_dir = Path("/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/image")
    lbl_dir = Path("/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/label")
    out_dir = Path("mobile/assets/roi_samples")

    generate_roi_samples(
        image_dir=img_dir,
        label_dir=lbl_dir,
        output_dir=out_dir,
        num_samples=30,
    )

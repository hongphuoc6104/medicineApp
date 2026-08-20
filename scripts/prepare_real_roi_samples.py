"""
scripts/prepare_real_roi_samples.py — Prepares R0 (Full Page) and R1 (Medication ROI Crop)
for 30 hard real-world camera captures from RX_001 and other validation prescriptions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrepareRealRoi")


def prepare_real_roi_dataset(
    rxie_root: Path,
    output_dir: Path,
    num_samples: int = 30,
):
    """Select 30 hard real camera captures and generate R0 and R1 crops."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = rxie_root / "data" / "manifests" / "prescriptions_manifest.json"
    ocr_final_dir = rxie_root / "data" / "ocr_final"
    gt_dir = rxie_root / "data" / "canonical_ground_truth"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Load P0 prediction metrics from previous benchmark to identify lowest-recall captures
    p0_pred_path = Path("reports/real_layout_ablation/p0_predictions.jsonl")
    hard_image_ids = []
    if p0_pred_path.exists():
        with open(p0_pred_path, "r", encoding="utf-8") as f:
            for line in f:
                p = json.loads(line)
                if p.get("prescription_id") == "RX_001":
                    hard_image_ids.append((p.get("image_id"), p.get("tp", 0), p.get("precision", 0)))
        # Sort by lowest TP
        hard_image_ids.sort(key=lambda x: (x[1], -x[2]))

    selected_rx001_ids = [item[0] for item in hard_image_ids[:20]] if hard_image_ids else []

    # Map image_id to prescription_id and image file path
    image_to_rx = {}
    image_paths = {}
    for g in manifest.get("groups", []):
        pid = g["prescription_id"]
        # Strictly exclude sealed test split
        if pid in ("RX_006", "RX_013", "RX_025", "RX_027"):
            continue
        rx_img_dir = rxie_root / "data" / "prescriptions" / pid / "images"
        for img in g.get("images", []):
            img_id = img["image_id"]
            image_to_rx[img_id] = pid
            fpath = rx_img_dir / img.get("filename", f"{img_id}.jpg")
            if fpath.exists():
                image_paths[img_id] = fpath

    # Build final list of 30 target captures
    target_img_ids = []
    for img_id in selected_rx001_ids:
        if img_id in image_paths and img_id not in target_img_ids:
            target_img_ids.append(img_id)

    # Add diverse captures from other prescriptions (RX_016, RX_019, RX_023, RX_002)
    other_pids = ["RX_016", "RX_019", "RX_023", "RX_002", "RX_003"]
    for pid in other_pids:
        for img_id, p in image_to_rx.items():
            if p == pid and img_id in image_paths and img_id not in target_img_ids:
                target_img_ids.append(img_id)
                if len(target_img_ids) >= num_samples:
                    break
        if len(target_img_ids) >= num_samples:
            break

    logger.info(f"Selected {len(target_img_ids)} hard real captures across {set(image_to_rx[i] for i in target_img_ids)}.")

    dataset_manifest = []

    for img_id in target_img_ids:
        pid = image_to_rx[img_id]
        img_path = image_paths[img_id]
        ocr_file = ocr_final_dir / f"{img_id}.json"
        gt_file = gt_dir / f"{pid}.json"

        if not gt_file.exists():
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        orig_img = Image.open(img_path).convert("RGB")
        w, h = orig_img.size

        # R0: Full Page Image
        r0_filename = f"r0_{img_id}.jpg"
        orig_img.save(output_dir / r0_filename, quality=95)

        # R1: Medication Table ROI Crop
        # Compute bounding box of medication section from OCR lines or standard prescription table bounds
        med_box = None
        if ocr_file.exists():
            with open(ocr_file, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
            cand_y_mins = []
            cand_y_maxs = []
            cand_x_mins = []
            cand_x_maxs = []
            for b in ocr_data.get("blocks", []):
                for l in b.get("lines", []):
                    t = l.get("text", "").lower()
                    box = l.get("boundingBox", {})
                    # Look for medication table indicators
                    if any(kw in t for kw in ["đơn thuốc", "thuốc điều trị", "thuốc", "viên", "ginkgo", "calcium", "vitamin", "amlor", "concor", "nexium", "ngày uống", "lần"]):
                        if "left" in box and "top" in box and "right" in box and "bottom" in box:
                            cand_x_mins.append(box["left"])
                            cand_y_mins.append(box["top"])
                            cand_x_maxs.append(box["right"])
                            cand_y_maxs.append(box["bottom"])

            if cand_y_mins and cand_y_maxs:
                # Expand box by 5% margin
                margin_x = int(w * 0.05)
                margin_y = int(h * 0.05)
                x_min = max(0, int(min(cand_x_mins)) - margin_x)
                y_min = max(0, int(min(cand_y_mins)) - margin_y)
                x_max = min(w, int(max(cand_x_maxs)) + margin_x)
                y_max = min(h, int(max(cand_y_maxs)) + margin_y)
                med_box = [x_min, y_min, x_max, y_max]

        # Fallback to standard medication table region (middle 55% of height) if no text hints
        if not med_box or (med_box[3] - med_box[1]) < int(h * 0.2):
            med_box = [
                int(w * 0.05),
                int(h * 0.25),
                int(w * 0.95),
                int(h * 0.85),
            ]

        r1_crop = orig_img.crop((med_box[0], med_box[1], med_box[2], med_box[3]))
        r1_filename = f"r1_{img_id}.jpg"
        r1_crop.save(output_dir / r1_filename, quality=95)

        dataset_manifest.append({
            "image_id": img_id,
            "prescription_id": pid,
            "orig_width": w,
            "orig_height": h,
            "r0_file": r0_filename,
            "r1_file": r1_filename,
            "r1_crop_box": med_box,
            "gt_medications": gt_data.get("medications", []),
        })

    manifest_out = output_dir / "real_roi_manifest.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(dataset_manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Generated {len(dataset_manifest)} sets of (R0, R1) images in {output_dir.resolve()}.")
    logger.info(f"Manifest saved to: {manifest_out.resolve()}")


if __name__ == "__main__":
    prepare_real_roi_dataset(
        rxie_root=Path("../medicineApp-rxie"),
        output_dir=Path("mobile/assets/real_roi_samples"),
        num_samples=30,
    )

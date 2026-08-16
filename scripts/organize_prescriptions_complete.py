#!/usr/bin/env python3
"""
Organizes both images and OCR results together by prescription:
data/prescriptions/
├── RX_001/
│   ├── canonical_gt.json
│   ├── metadata.json
│   ├── images/
│   │   ├── IMG_20260209_002313.jpg
│   │   └── ...
│   └── ocr_final/
│       ├── IMG_20260209_002313.json
│       └── ...
├── RX_002/
│   └── ...
└── hard_cases/
    ├── RX_026/
    └── ...
"""

import glob
import json
import os
import shutil


def link_or_copy(src_path: str, dst_path: str):
    """Creates a hardlink if possible, else copies the file."""
    if os.path.exists(dst_path):
        os.remove(dst_path)
    try:
        os.link(src_path, dst_path)
    except Exception:
        shutil.copy2(src_path, dst_path)


def main():
    manifest_path = "data/manifests/prescriptions_manifest.json"
    gt_dir = "data/canonical_ground_truth"
    ocr_final_dir = "data/ocr_final"
    input_root = "data/input"
    output_root = "data/prescriptions"

    os.makedirs(output_root, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Index all input image files by base image_id
    raw_images = glob.glob(f"{input_root}/**/*.*", recursive=True)
    img_map = {}
    for p in raw_images:
        ext = os.path.splitext(p)[1].lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            iid = os.path.splitext(os.path.basename(p))[0]
            if iid not in img_map:
                img_map[iid] = p

    print("==================================================================")
    print("   RxIE Full Dataset Organizer (Images + OCR + GT by Prescription)")
    print("==================================================================")
    print(f"[*] Found {len(img_map)} source images in {input_root}/")

    total_images_organized = 0
    total_ocrs_organized = 0

    for g in manifest["groups"]:
        rx_id = g["prescription_id"]
        status = g["grouping_status"]

        if status == "verified":
            rx_folder = os.path.join(output_root, rx_id)
        else:
            rx_folder = os.path.join(output_root, "hard_cases", rx_id)

        rx_img_dir = os.path.join(rx_folder, "images")
        rx_ocr_dir = os.path.join(rx_folder, "ocr_final")
        os.makedirs(rx_img_dir, exist_ok=True)
        os.makedirs(rx_ocr_dir, exist_ok=True)

        # 1. Canonical Ground Truth
        gt_source = os.path.join(gt_dir, f"{rx_id}.json")
        if os.path.exists(gt_source):
            shutil.copy2(gt_source, os.path.join(rx_folder, "canonical_gt.json"))

        # 2. Metadata
        meta_file = os.path.join(rx_folder, "metadata.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "prescription_id": rx_id,
                "patient_id": g["patient_id"],
                "hospital_hint": g.get("hospital_hint"),
                "encounter_code_hint": g.get("encounter_code_hint"),
                "diagnoses_hint": g.get("diagnoses_hint"),
                "grouping_status": status,
                "image_count": g["image_count"],
                "images": g["images"],
            }, f, ensure_ascii=False, indent=2)

        # 3. Organize Images & OCR
        img_count = 0
        ocr_count = 0
        for img_info in g["images"]:
            iid = img_info["image_id"]

            # Image
            if iid in img_map:
                src_img = img_map[iid]
                ext = os.path.splitext(src_img)[1]
                dst_img = os.path.join(rx_img_dir, f"{iid}{ext}")
                link_or_copy(src_img, dst_img)
                img_count += 1

            # OCR Final JSON
            ocr_src = os.path.join(ocr_final_dir, f"{iid}.json")
            if os.path.exists(ocr_src):
                dst_ocr = os.path.join(rx_ocr_dir, f"{iid}.json")
                link_or_copy(ocr_src, dst_ocr)
                ocr_count += 1

        total_images_organized += img_count
        total_ocrs_organized += ocr_count
        print(f"[+] {rx_id:<8} ({status:<12}): {img_count:>3} images, {ocr_count:>3} OCR files -> {rx_folder}")

    print("==================================================================")
    print(f"✅ Successfully organized {len(manifest['groups'])} prescriptions:")
    print(f"    - Total Images linked : {total_images_organized}/437")
    print(f"    - Total OCR files     : {total_ocrs_organized}/437")
    print(f"📍 Root directory         : {output_root}/")
    print("==================================================================\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Exports physically grouped prescription folders:
data/prescriptions/
├── RX_001/
│   ├── canonical_gt.json
│   ├── metadata.json
│   └── ocr_final/
│       ├── IMG_20260115_181847.json
│       └── ...
├── RX_002/
│   └── ...
└── hard_cases/
    ├── metadata.json
    └── ocr_final/
        └── ...
"""

import glob
import json
import os
import shutil


def main():
    manifest_path = "data/manifests/prescriptions_manifest.json"
    gt_dir = "data/canonical_ground_truth"
    ocr_final_dir = "data/ocr_final"
    output_root = "data/prescriptions"

    os.makedirs(output_root, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("==================================================================")
    print("   RxIE Exporting Physically Grouped Prescription Folders         ")
    print("==================================================================")

    created_groups = 0
    total_images_copied = 0

    for g in manifest["groups"]:
        rx_id = g["prescription_id"]
        status = g["grouping_status"]

        if status == "verified":
            rx_folder = os.path.join(output_root, rx_id)
        else:
            rx_folder = os.path.join(output_root, "hard_cases", rx_id)

        rx_ocr_dir = os.path.join(rx_folder, "ocr_final")
        os.makedirs(rx_ocr_dir, exist_ok=True)

        # 1. Copy Canonical GT if available
        gt_source = os.path.join(gt_dir, f"{rx_id}.json")
        if os.path.exists(gt_source):
            shutil.copy2(gt_source, os.path.join(rx_folder, "canonical_gt.json"))

        # 2. Save metadata.json
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

        # 3. Copy OCR final files belonging to this prescription
        copied_in_group = 0
        for img in g["images"]:
            iid = img["image_id"]
            ocr_src = os.path.join(ocr_final_dir, f"{iid}.json")
            if os.path.exists(ocr_src):
                shutil.copy2(ocr_src, os.path.join(rx_ocr_dir, f"{iid}.json"))
                copied_in_group += 1

        created_groups += 1
        total_images_copied += copied_in_group
        print(f"[+] {rx_id:<8} ({status:<8}): {copied_in_group:>3} images -> {rx_folder}")

    print("==================================================================")
    print(f"✅ Successfully created {created_groups} prescription folders with {total_images_copied} OCR files.")
    print(f"📍 Location: {output_root}/")
    print("==================================================================\n")


if __name__ == "__main__":
    main()

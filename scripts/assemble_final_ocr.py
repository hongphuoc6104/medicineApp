#!/usr/bin/env python3
"""
Assembles OCR_FINAL (RxIE Preprocessing V1 Frozen):
1. For the 200 benchmark images: assembles final OCR JSONs directly from existing P0/P1/P4 outputs
   based on the frozen P6 selector log.
2. For the 237 remaining captures: prepares the input list for running only the frozen pipeline
   (Orientation Correction + Conditional Deskew).
"""

import glob
import json
import os
import shutil
import sys


def main():
    spec_path = "data/manifests/preprocessing_v1_frozen_spec.json"
    manifest_path = "data/manifests/prescriptions_manifest.json"
    output_final_dir = "data/ocr_final"
    os.makedirs(output_final_dir, exist_ok=True)

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    selections = spec.get("selections_200_benchmark", {})

    branch_dirs = {
        "P0": "data/output",
        "P1": "data/output_p1",
        "P4": "data/output_rectified",
    }

    all_200_staged = set(selections.keys())
    all_437_images = set()
    for g in manifest["groups"]:
        for img in g["images"]:
            all_437_images.add(img["image_id"])

    remaining_237 = sorted(list(all_437_images - all_200_staged))

    print("==================================================================")
    print("        RxIE OCR_FINAL Dataset Assembler (V1 Frozen)              ")
    print("==================================================================")
    print(f"[*] Benchmark Images (200) : Assembling from existing P0/P1/P4 branches...")

    assembled_count = 0
    branch_usage = {"P0": 0, "P1": 0, "P4": 0}

    for iid, branch_choice in selections.items():
        src_dir = branch_dirs.get(branch_choice, "data/output")
        # Find file in src_dir
        matches = glob.glob(f"{src_dir}/**/{iid}.json", recursive=True)
        if matches:
            src_file = matches[0]
            dst_file = os.path.join(output_final_dir, f"{iid}.json")
            shutil.copy2(src_file, dst_file)
            assembled_count += 1
            branch_usage[branch_choice] += 1

    print(f"[+] Successfully assembled {assembled_count}/200 OCR_FINAL files:")
    for b, count in branch_usage.items():
        print(f"    - From {b:<2} : {count} images ({count/assembled_count*100:.1f}%)")

    print(f"\n[*] Remaining Images to Process ({len(remaining_237)}):")
    print(f"    - Only need to run Frozen Preprocessing V1 (Rotation + Conditional Deskew)")
    print(f"    - No need to run full P1/P2/P3/P4 branches separately!")

    plan_path = "data/manifests/remaining_237_processing_plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({
            "description": "237 Captures to be processed with Preprocessing V1 Frozen spec.",
            "total_count": len(remaining_237),
            "pipeline_spec": spec["rules"],
            "image_ids": remaining_237,
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ Exported execution plan for remaining 237 images -> {plan_path}")
    print("==================================================================\n")


if __name__ == "__main__":
    main()

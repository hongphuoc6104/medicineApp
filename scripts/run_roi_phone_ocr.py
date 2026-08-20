"""
scripts/run_roi_phone_ocr.py — Runs on-device C0/C1/C2 ML Kit OCR on connected Android device
and executes the complete 3-Tier ROI ablation benchmark.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from pathlib import Path

from scripts.benchmark_roi_ablation import run_roi_ablation_eval

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RoiPhoneOCR")


def run_roi_phone_ocr_and_eval(
    device_id: str,
    output_dir: Path,
    gt_dir: Path,
):
    """Run Flutter C0/C1/C2 ML Kit test runner on Android device and stream OCR results."""
    mlkit_ocr_dir = output_dir / "mlkit_ocr"
    mlkit_ocr_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "flutter",
        "test",
        "integration_test/roi_batch_ocr_runner.dart",
        "-d",
        device_id,
    ]

    logger.info(f"Launching C0/C1/C2 Flutter ML Kit OCR runner on Android device: {device_id}...")
    logger.info(f"Command: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        cwd="mobile",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    captured_jsons = 0
    in_json_block = False
    current_json_lines = []

    for line in iter(process.stdout.readline, ""):
        line_strip = line.strip()

        if "[ROI_OCR_JSON_START]" in line_strip:
            in_json_block = True
            current_json_lines = []
            continue
        elif "[ROI_OCR_JSON_END]" in line_strip:
            in_json_block = False
            json_text = "\n".join(current_json_lines).strip()
            if json_text:
                try:
                    data = json.loads(json_text)
                    tier = data.get("tier", "c0")
                    img_id = data.get("image_id", f"capture_{captured_jsons}")
                    out_path = mlkit_ocr_dir / f"{tier}_{img_id}.json"
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    captured_jsons += 1
                    logger.info(f"Captured on-device OCR for: {tier}_{img_id}.json ({data.get('line_count', 0)} lines)")
                except Exception as e:
                    logger.error(f"Failed to parse captured JSON: {e}")
            continue

        if in_json_block:
            current_json_lines.append(line)
        else:
            if line_strip.startswith("[INFO]") or line_strip.startswith("[DONE]") or line_strip.startswith("["):
                print(line_strip)
            elif "Running Gradle task" in line_strip or "Built build" in line_strip or "Installing build" in line_strip:
                print(line_strip)

    process.wait()
    logger.info(f"On-device OCR complete! Captured {captured_jsons} ML Kit OCR files in {mlkit_ocr_dir.resolve()}.")

    # Run Benchmark Evaluation
    logger.info("Executing 3-Tier ROI ablation evaluation...")
    run_roi_ablation_eval(
        ocr_dir=mlkit_ocr_dir,
        gt_dir=gt_dir,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run on-device C0/C1/C2 ML Kit OCR on Android phone and benchmark")
    parser.add_argument("--device", type=str, default="192.168.1.63:45267", help="Device ID / IP:Port from adb devices")
    parser.add_argument("--output-dir", type=str, default="reports/medication_roi_ablation", help="Output directory for reports")
    parser.add_argument("--gt-dir", type=str, default="/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/label", help="VAIPE Ground truth labels directory")
    args = parser.parse_args()

    run_roi_phone_ocr_and_eval(
        device_id=args.device,
        output_dir=Path(args.output_dir),
        gt_dir=Path(args.gt_dir),
    )

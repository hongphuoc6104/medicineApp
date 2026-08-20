"""
scripts/run_vaipe_phone_ocr.py — Orchestrates on-device ML Kit OCR execution on Android phone
and runs the 4-stage end-to-end evaluation pipeline.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
from pathlib import Path

from scripts.benchmark_vaipe_end2end import run_vaipe_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VaipePhoneOCR")


def run_phone_ocr_and_eval(
    device_id: str,
    output_dir: Path,
    gt_dir: Path,
    limit: int | None = None,
):
    """Run Flutter ML Kit test runner on Android device and stream OCR results."""
    mlkit_ocr_dir = output_dir / "mlkit_ocr"
    mlkit_ocr_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "flutter",
        "test",
        "integration_test/vaipe_batch_ocr_runner.dart",
        "-d",
        device_id,
    ]

    logger.info(f"Launching Flutter ML Kit OCR runner on Android device: {device_id}...")
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

        if "[VAIPE_OCR_JSON_START]" in line_strip:
            in_json_block = True
            current_json_lines = []
            continue
        elif "[VAIPE_OCR_JSON_END]" in line_strip:
            in_json_block = False
            json_text = "\n".join(current_json_lines).strip()
            if json_text:
                try:
                    data = json.loads(json_text)
                    img_id = data.get("image_id", f"capture_{captured_jsons}")
                    out_path = mlkit_ocr_dir / f"{img_id}.json"
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    captured_jsons += 1
                    logger.info(f"Saved real ML Kit OCR for: {img_id}.json ({data.get('line_count', 0)} lines)")
                except Exception as e:
                    logger.error(f"Failed to parse captured JSON: {e}")
            continue

        if in_json_block:
            current_json_lines.append(line)
        else:
            if line_strip.startswith("[INFO]") or line_strip.startswith("[PROCESSED]") or line_strip.startswith("[DONE]"):
                print(line_strip)
            elif "Running Gradle task" in line_strip or "Built build" in line_strip or "Installing build" in line_strip:
                print(line_strip)

    process.wait()
    logger.info(f"On-device OCR complete! Captured {captured_jsons} ML Kit OCR files in {mlkit_ocr_dir.resolve()}.")

    # Now run the 4-stage benchmark evaluation
    logger.info("Proceeding to 4-stage pipeline evaluation...")
    run_vaipe_benchmark(
        ocr_dir=mlkit_ocr_dir,
        gt_dir=gt_dir,
        output_dir=output_dir,
        limit=limit,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run on-device ML Kit OCR on Android phone and benchmark")
    parser.add_argument("--device", type=str, default="192.168.1.63:45267", help="Device ID / IP:Port from adb devices")
    parser.add_argument("--output-dir", type=str, default="reports/vaipe_mlkit_end2end", help="Output directory for reports")
    parser.add_argument("--gt-dir", type=str, default="/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/label", help="VAIPE Ground truth labels directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images")
    args = parser.parse_args()

    run_vaipe_phone_ocr_and_eval = run_phone_ocr_and_eval(
        device_id=args.device,
        output_dir=Path(args.output_dir),
        gt_dir=Path(args.gt_dir),
        limit=args.limit,
    )

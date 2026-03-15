import os
import sys
import time
import json
import cv2
import torch
import numpy as np
from pathlib import Path

# Add root to sys.path
ROOT = str(Path(__file__).resolve().parents[2])
sys.path.append(ROOT)

from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule, group_by_stt
from core.phase_a.s3_ocr.base import OcrResult, TextBlock as _TB

def test_ocr_detailed(image_path, out_dir):
    """
    Test script to demonstrate detailed OCR steps as requested by USER.
    Follows AGENTS.md rule of using a separate test file for new logging/logic.
    """
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n[TEST] Processing: {image_path}")
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Cannot read image {image_path}")
        return

    # Initialize OCR Module
    device = "gpu" if torch.cuda.is_available() else "cpu"
    ocr = HybridOcrModule(device=device)
    
    t0_ocr = time.time()
    
    # ── 3.1: Text Detection ───────────────────────────────────────────────
    print(f"\n  ▸ Step 3.1: Text Detection (PaddleOCR)")
    t1 = time.time()
    ocr._ensure_detector()
    polys = ocr._detect_polys(img)
    t_det = time.time() - t1
    print(f"    ✅ Done in {t_det:.1f}s | Found {len(polys)} regions")
    
    for i, poly in enumerate(polys[:5]):
        coords = ",".join([f"{int(p[0])},{int(p[1])}" for p in poly])
        print(f"      [D] Region {i+1:02d}: [{coords}]")

    # ── 3.2: Text Recognition ─────────────────────────────────────────────
    print(f"\n  ▸ Step 3.2: Text Recognition (VietOCR)")
    t2 = time.time()
    ocr._ensure_recognizer()
    text_blocks = ocr._recognize_batch(img, polys)
    t_rec = time.time() - t2
    print(f"    ✅ Done in {t_rec:.1f}s | Recognized {len(text_blocks)} blocks")
    
    for i, b in enumerate(text_blocks[:10]):
        print(f"      [R] Block {i+1:02d}: \"{b.text}\" (conf: {b.confidence:.2f})")

    # ── 3.3: Visualization ───────────────────────────────────────────────
    print(f"\n  ▸ Step 3.3: Saving Results")
    full_result = OcrResult(
        text_blocks=text_blocks,
        module_name="hybrid",
        input_type="raw_test",
        elapsed_ms=(time.time() - t0_ocr) * 1000
    )
    # Save using base class method
    ocr.save_results(full_result, img, "test_ocr_raw", out_dir, out_dir, out_dir)
    print(f"    ✅ Saved visualization: {out_dir}/test_ocr_raw_det.png")
    print(f"    ✅ Saved raw text:      {out_dir}/test_ocr_raw.txt")

    # ── 3.4: STT Grouping (Check) ─────────────────────────────────────────
    print(f"\n  ▸ Step 3.4: STT Grouping (Experimental)")
    t3 = time.time()
    merged_blocks_obj = group_by_stt(text_blocks)
    t_stt = time.time() - t3
    print(f"    ✅ Done in {t_stt:.2f}s | {len(text_blocks)} -> {len(merged_blocks_obj)} lines")
    
    stt_result = OcrResult(
        text_blocks=[_TB(text=b.text, confidence=b.confidence, bbox=b.bbox) for b in merged_blocks_obj],
        module_name="hybrid",
        input_type="merged_test",
        elapsed_ms=t_stt * 1000
    )
    ocr.save_results(stt_result, img, "test_ocr_stt", out_dir, out_dir, out_dir)
    print(f"    ✅ Saved STT visualization: {out_dir}/test_ocr_stt_det.png")
    
    print(f"\n[TEST COMPLETED] Total OCR time: {time.time()-t0_ocr:.1f}s")
    print(f"All files saved to: {out_dir}")

if __name__ == "__main__":
    # Default test image
    IMG = "data/input/prescription_1/IMG_20260209_180412.jpg"
    OUT = "data/output/tests/ocr_detailed"
    
    if len(sys.argv) > 1:
        IMG = sys.argv[1]
    
    test_ocr_detailed(IMG, OUT)

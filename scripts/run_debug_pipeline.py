"""
run_debug_pipeline.py — Chạy 1 ảnh qua toàn pipeline, lưu kết quả từng bước.

Mỗi lần chạy: dọn sạch output/debug_run/ trước → lưu rõ từng bước để xem.

Steps:
  step-1_input.jpg          ← Ảnh gốc crop
  step-2_deskewed.png       ← Sau deskew (chỉ lưu nếu bị nghiêng)
  step-2_fixed.png          ← Sau AI fix 180°
  step-3_detection.png      ← PaddleOCR bbox overlay
  step-3_ocr.json           ← OCR JSON (text + bbox)
  step-3_ocr.txt            ← OCR raw text (1 dòng/block)
  step-4_grouped.json       ← Sau khi merge_same_line + group_drug_lines
  step-4_grouped.txt        ← Grouped text (dễ đọc)
  step-5_drug_mapper.json   ← Kết quả DrugMapper
  step-5_drug_mapper.txt    ← Chỉ các thuốc matched
  summary.txt               ← Tổng kết toàn bộ

Chạy:
  python scripts/run_debug_pipeline.py [--gpu] [--image mask|bbox]
"""

import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix PaddlePaddle MKLDNN bug
os.environ.setdefault("FLAGS_enable_pir_api", "0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("debug_pipeline")

DEBUG_DIR = "output/debug_run"
SAMPLE_IMG = "IMG_20260209_180420"


# ── Bước 0: Dọn dẹp ──────────────────────────────────────────────────────────

def clean_debug_dir():
    """Xóa hết kết quả cũ trước khi chạy."""
    if os.path.isdir(DEBUG_DIR):
        shutil.rmtree(DEBUG_DIR)
    os.makedirs(DEBUG_DIR)
    logger.info(f"Cleaned: {DEBUG_DIR}/")


# ── Bước 1: Load ảnh ─────────────────────────────────────────────────────────

def step0_yolo(raw_path: str):
    """Step 0: YOLO detection + crop (nếu input là raw image)."""
    from core.detector import PrescriptionDetector
    from core.segmentation import crop_by_mask

    img = cv2.imread(raw_path)
    if img is None:
        logger.error(f"Cannot read: {raw_path}")
        sys.exit(1)

    detector = PrescriptionDetector()
    results = detector.predict(img)

    if not results or results[0].masks is None:
        logger.error("YOLO: No prescription detected!")
        sys.exit(1)

    cropped = crop_by_mask(img, results[0])
    if cropped is None:
        logger.error("YOLO: crop failed")
        sys.exit(1)

    cv2.imwrite(
        os.path.join(DEBUG_DIR, "step-0_yolo_crop.jpg"), cropped
    )
    logger.info(
        f"Step 0 ✅ YOLO: {img.shape[1]}x{img.shape[0]}"
        f" → {cropped.shape[1]}x{cropped.shape[0]}"
    )
    return cropped


def step1_load(input_type="mask", raw_path=None):
    """Load ảnh: từ pre-cropped hoặc raw+YOLO."""
    if raw_path:
        # Chạy YOLO để crop
        img = step0_yolo(raw_path)
    else:
        path = (
            f"data/output/{input_type}/"
            f"{SAMPLE_IMG}_{input_type}.png"
        )
        if not os.path.isfile(path):
            logger.error(f"Not found: {path}")
            sys.exit(1)
        img = cv2.imread(path)

    cv2.imwrite(
        os.path.join(DEBUG_DIR, "step-1_input.jpg"), img
    )
    logger.info(
        f"Step 1 ✅ Input: {img.shape[1]}x{img.shape[0]}"
    )
    return img


# ── Bước 2: Preprocess ───────────────────────────────────────────────────────

def step2_preprocess(image):
    from core.preprocessor.orientation import preprocess_image
    processed, info = preprocess_image(image, stem="step-2", save_dir=DEBUG_DIR)
    logger.info(
        f"Step 2 ✅ Preprocess: "
        f"deskew={info['deskew_angle']}°, "
        f"portrait={info['portrait_rotated']}, "
        f"ai={info['ai_status']}"
    )
    return processed, info


# ── Bước 3: OCR ──────────────────────────────────────────────────────────────

def step3_ocr(image, use_gpu=False):
    from core.ocr.ocr_engine import HybridOcrModule

    device = "cuda" if use_gpu else "cpu"

    # Resize nếu ảnh quá lớn (tránh PaddleOCR OOM)
    MAX_DIM = 1600
    h, w = image.shape[:2]
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h),
                           interpolation=cv2.INTER_LINEAR)
        logger.info(f"  Resized: {w}x{h} → {new_w}x{new_h} "
                    f"(scale={scale:.2f})")
        cv2.imwrite(
            os.path.join(DEBUG_DIR, "step-3_resized.png"), image
        )

    module = HybridOcrModule(device=device)
    result = module.extract(image, input_type="mask")

    # Detection overlay
    module.save_results(
        result, image, "step-3",
        DEBUG_DIR, DEBUG_DIR, DEBUG_DIR,
    )
    # Rename generated files → step-3_* names
    for old, new in [
        ("step-3_det.png", "step-3_detection.png"),
    ]:
        src = os.path.join(DEBUG_DIR, old)
        dst = os.path.join(DEBUG_DIR, new)
        if os.path.exists(src):
            os.replace(src, dst)

    # Save JSON
    ocr_dict = {
        "module": result.module_name,
        "elapsed_ms": result.elapsed_ms,
        "block_count": len(result.text_blocks),
        "blocks": [
            {
                "text": b.text,
                "confidence": round(b.confidence, 4),
                "bbox": b.bbox,
            }
            for b in result.text_blocks
        ],
    }
    json_path = os.path.join(DEBUG_DIR, "step-3_ocr.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ocr_dict, f, ensure_ascii=False, indent=2)

    # Save txt (1 block per line)
    txt_path = os.path.join(DEBUG_DIR, "step-3_ocr.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for i, b in enumerate(result.text_blocks):
            f.write(f"[{i:02d}] {b.text}\n")

    logger.info(
        f"Step 3 ✅ OCR: {len(result.text_blocks)} blocks "
        f"in {result.elapsed_ms:.0f}ms"
    )
    return result, json_path


# ── Bước 4: Grouping ─────────────────────────────────────────────────────────

def step4_grouping(ocr_json_path):
    """Áp dụng merge_same_line + group_drug_lines, lưu trước/sau để so sánh."""
    from core.converter.ocr_to_pima import OcrToPimaConverter

    with open(ocr_json_path, encoding="utf-8") as f:
        data = json.load(f)
    raw_blocks = data["blocks"]

    # Bước 4a: merge same-line
    same_line = OcrToPimaConverter.merge_same_line_blocks(raw_blocks)
    # Bước 4b: cross-line drug grouping
    grouped = OcrToPimaConverter.group_drug_lines(same_line)

    # Save JSON
    grouped_json = {
        "raw_count": len(raw_blocks),
        "after_same_line": len(same_line),
        "after_grouping": len(grouped),
        "blocks": [
            {
                "text": b.get("text", ""),
                "confidence": b.get("confidence", 0),
            }
            for b in grouped
        ],
    }
    json_path = os.path.join(DEBUG_DIR, "step-4_grouped.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(grouped_json, f, ensure_ascii=False, indent=2)

    # Save txt — dễ đọc
    txt_path = os.path.join(DEBUG_DIR, "step-4_grouped.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Raw blocks:      {len(raw_blocks)}\n")
        f.write(f"After same-line: {len(same_line)}\n")
        f.write(f"After grouping:  {len(grouped)}\n")
        f.write("-" * 40 + "\n")
        for i, b in enumerate(grouped):
            f.write(f"[{i:02d}] {b.get('text', '')}\n")

    logger.info(
        f"Step 4 ✅ Grouping: "
        f"{len(raw_blocks)} raw → {len(same_line)} same-line "
        f"→ {len(grouped)} final"
    )
    return grouped


# ── Bước 5: DrugMapper ────────────────────────────────────────────────────────

def step5_drug_mapper(grouped_blocks):
    from core.converter.drug_lookup import DrugLookup

    lookup = DrugLookup()  # Local VN DB only
    results = []
    matched = []

    # Keywords chỉ ra block NOT phải tên thuốc
    SKIP_PATTERNS = {
        "bộ y tế", "đơn thuốc", "điện thoại", "họ tên", "tuổi",
        "giới tính", "mã số", "bhyt", "địa chỉ", "chẩn đoán",
        "chấn đoán", "stt", "thuốc điều trị", "thuoc", "van co",
        "văn cơ", "bvđk", "bệnh viện",
    }
    MIN_SCORE = 0.3   # Bỏ qua kết quả không đủ tin cậy

    for b in grouped_blocks:
        # Skip dosage blocks
        if b.get("label") == "dosage":
            continue
        text = b.get("text", "").strip()
        if not text or len(text) < 5:
            continue

        # Skip header/non-drug blocks
        text_lower = text.lower()
        if any(kw in text_lower for kw in SKIP_PATTERNS):
            continue

        r = lookup.lookup(text)

        # Only accept results with sufficient confidence
        is_match = r["name"] and r["score"] >= MIN_SCORE
        results.append({
            "ocr_text":     text,
            "matched_drug": r["name"],
            "score":        round(r["score"], 3),
            "source":       r["source"],
            "category":     r.get("category"),
            "status":       "matched" if is_match
                            else "no_match",
        })
        if is_match:
            matched.append(r["name"])

    # Save JSON
    json_path = os.path.join(DEBUG_DIR, "step-5_drug_mapper.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Save txt
    txt_path = os.path.join(DEBUG_DIR, "step-5_drug_mapper.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Drugs matched: {len(matched)}/{len(results)}\n")
        f.write("-" * 40 + "\n")
        for r in results:
            if r["status"] == "matched":
                src = r["source"] or ""
                f.write(
                    f"  [{src:8s}] [{r['score']:.2f}] "
                    f"'{r['ocr_text']}'"
                    f" → {r['matched_drug']}\n"
                )
        f.write("\n--- All results ---\n")
        for r in results:
            mark = "✅" if r["status"] == "matched" else "  "
            src = r.get("source") or "-"
            f.write(
                f"{mark} [{src:8s}] "
                f"[{r['score']:.2f}] {r['ocr_text']}\n"
            )

    logger.info(
        f"Step 5 ✅ DrugMapper(API): "
        f"{len(matched)}/{len(results)} matched"
    )
    return matched, results



# ── Summary ───────────────────────────────────────────────────────────────────

def write_summary(prep_info, n_ocr, ms_ocr, n_grouped, matched_drugs, elapsed):
    files = sorted(os.listdir(DEBUG_DIR))
    lines = [
        "=" * 55,
        "  DEBUG PIPELINE SUMMARY",
        "=" * 55,
        f"  Image:   {SAMPLE_IMG}",
        f"  Time:    {elapsed:.1f}s total",
        "",
        f"  Step 2 — Preprocess",
        f"    deskew:   {prep_info['deskew_angle']}°",
        f"    portrait: {prep_info['portrait_rotated']}",
        f"    ai_fix:   {prep_info['ai_status']}",
        "",
        f"  Step 3 — OCR",
        f"    blocks:  {n_ocr}",
        f"    time:    {ms_ocr:.0f}ms",
        "",
        f"  Step 4 — Grouping",
        f"    final:   {n_grouped} blocks",
        "",
        f"  Step 5 — DrugMapper",
        f"    matched: {matched_drugs}",
        "",
        "  Files:",
    ]
    for fn in files:
        sz = os.path.getsize(os.path.join(DEBUG_DIR, fn))
        lines.append(f"    {fn:35s} {sz:>8,} bytes")
    lines.append("=" * 55)

    text = "\n".join(lines)
    with open(os.path.join(DEBUG_DIR, "summary.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    print("\n" + text)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--image", default="mask",
                        choices=["mask", "bbox"])
    parser.add_argument(
        "--raw", type=str, default=None,
        help="Raw image path → run YOLO first",
    )
    args = parser.parse_args()

    t0 = time.time()

    # Dọn dẹp kết quả cũ
    clean_debug_dir()

    img = step1_load(args.image, raw_path=args.raw)
    processed, prep_info = step2_preprocess(img)
    result, ocr_json_path = step3_ocr(
        processed, use_gpu=args.gpu
    )
    grouped = step4_grouping(ocr_json_path)
    matched, all_results = step5_drug_mapper(grouped)

    write_summary(
        prep_info,
        n_ocr=len(result.text_blocks),
        ms_ocr=result.elapsed_ms,
        n_grouped=len(grouped),
        matched_drugs=matched,
        elapsed=time.time() - t0,
    )
    print(f"\n✅ Done in {time.time() - t0:.1f}s")
    print(f"📂 {os.path.abspath(DEBUG_DIR)}/")


if __name__ == "__main__":
    main()

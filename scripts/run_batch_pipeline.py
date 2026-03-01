"""
run_batch_pipeline.py — Chạy pipeline trên nhiều ảnh raw input.

Mỗi ảnh → thư mục output/batch_run/<tên_ảnh>/ với toàn bộ kết quả từng bước.

Chạy:
  python scripts/run_batch_pipeline.py
  python scripts/run_batch_pipeline.py --images data/input/IMG_20260209_180410.jpg ...
  python scripts/run_batch_pipeline.py --gpu
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
logger = logging.getLogger("batch_pipeline")

BATCH_DIR = "output/batch_run"
MAX_DIM = 1600

# Keywords để skip block không phải tên thuốc
SKIP_PATTERNS = {
    "bộ y tế", "đơn thuốc", "điện thoại", "họ tên", "tuổi",
    "giới tính", "mã số", "bhyt", "địa chỉ", "chẩn đoán",
    "chấn đoán", "stt", "thuốc điều trị", "van co",
    "văn cơ", "bvđk", "bệnh viện",
}
MIN_DRUG_SCORE = 0.3


# ── Helper ──────────────────────────────────────────────────────────────────

def resize_if_needed(img):
    h, w = img.shape[:2]
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        img = cv2.resize(
            img, (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_LINEAR,
        )
    return img


# ── Per-image pipeline ───────────────────────────────────────────────────────

def process_image(
    img_path: str,
    out_dir: str,
    ocr_module=None,
    drug_lookup=None,
    detector=None,
    use_gpu: bool = False,
) -> dict:
    """
    Chạy toàn bộ pipeline cho 1 ảnh, lưu kết quả vào out_dir.
    Accepts shared modules for singleton reuse.
    Returns summary dict.
    """
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    stem = Path(img_path).stem

    # ── Step 1: Load ──────────────────────────────────────────────────────
    img = cv2.imread(img_path)
    if img is None:
        logger.error(f"Cannot read: {img_path}")
        return {"image": stem, "error": "cannot_read"}
    cv2.imwrite(os.path.join(out_dir, "step-0_raw.jpg"), img)

    # ── Step 0.5: YOLO Detect + Crop ─────────────────────────────────────
    if detector is not None:
        from core.segmentation import crop_by_mask
        yolo_results = detector.predict(img)
        if yolo_results and yolo_results[0].masks is not None:
            cropped = crop_by_mask(img, yolo_results[0])
            if cropped is not None:
                img = cropped
                logger.info(
                    f"  YOLO: cropped to "
                    f"{img.shape[1]}x{img.shape[0]}"
                )
            else:
                logger.warning("  YOLO: crop failed")
        else:
            logger.warning("  YOLO: no detection")

    cv2.imwrite(os.path.join(out_dir, "step-1_input.jpg"), img)

    # ── Step 2: Preprocess ───────────────────────────────────────────────
    from core.preprocessor.orientation import preprocess_image
    processed, prep_info = preprocess_image(
        img, stem="step-2", save_dir=out_dir,
    )
    processed = resize_if_needed(processed)
    cv2.imwrite(os.path.join(out_dir, "step-2_resized.png"), processed)

    # ── Step 3: OCR (singleton) ──────────────────────────────────────────
    if ocr_module is None:
        from core.ocr.ocr_engine import HybridOcrModule
        device = "cuda" if use_gpu else "cpu"
        ocr_module = HybridOcrModule(device=device)
    result = ocr_module.extract(processed, input_type="raw")
    # save_results kế thừa từ BaseOCR
    ocr_module.save_results(
        result, processed, "step-3",
        out_dir, out_dir, out_dir,
    )

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
    ocr_json_path = os.path.join(out_dir, "step-3_ocr.json")
    with open(ocr_json_path, "w", encoding="utf-8") as f:
        json.dump(ocr_dict, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(out_dir, "step-3_ocr.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for i, b in enumerate(result.text_blocks):
            f.write(f"[{i:02d}] {b.text}\n")

    # ── Step 4: Grouping ─────────────────────────────────────────────────
    from core.converter.ocr_to_pima import OcrToPimaConverter
    raw_blocks = ocr_dict["blocks"]
    same_line = OcrToPimaConverter.merge_same_line_blocks(raw_blocks)
    grouped = OcrToPimaConverter.group_drug_lines(same_line)

    grouped_json = {
        "raw_count": len(raw_blocks),
        "after_same_line": len(same_line),
        "after_grouping": len(grouped),
        "blocks": [
            {
                "text": b.get("text", ""),
                "label": b.get("label", "drug"),
            }
            for b in grouped
        ],
    }
    with open(os.path.join(out_dir, "step-4_grouped.json"),
              "w", encoding="utf-8") as f:
        json.dump(grouped_json, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "step-4_grouped.txt"),
              "w", encoding="utf-8") as f:
        f.write(f"Raw: {len(raw_blocks)} | "
                f"Same-line: {len(same_line)} | "
                f"Grouped: {len(grouped)}\n")
        f.write("-" * 40 + "\n")
        for i, b in enumerate(grouped):
            label = b.get("label", "")
            tag = "[dosage]" if label == "dosage" else ""
            f.write(f"[{i:02d}]{tag} {b.get('text', '')}\n")

    # ── Step 5: Drug Lookup (local VN DB) ─────────────────────────────────
    if drug_lookup is None:
        from core.converter.drug_lookup import DrugLookup
        drug_lookup = DrugLookup()
    drug_results, matched = [], []

    for b in grouped:
        if b.get("label") == "dosage":
            continue
        text = b.get("text", "").strip()
        if not text or len(text) < 5:
            continue
        if any(kw in text.lower() for kw in SKIP_PATTERNS):
            continue

        r = drug_lookup.lookup(text)
        is_match = r["name"] and r["score"] >= MIN_DRUG_SCORE
        drug_results.append({
            "ocr_text": text,
            "matched_drug": r["name"],
            "generic": r.get("generic", ""),
            "score": round(r["score"], 3),
            "source": r["source"],
            "category": r.get("category", ""),
            "status": "matched" if is_match else "no_match",
        })
        if is_match:
            matched.append(r["name"])

    with open(os.path.join(out_dir, "step-5_drug_lookup.json"),
              "w", encoding="utf-8") as f:
        json.dump(drug_results, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "step-5_drug_lookup.txt"),
              "w", encoding="utf-8") as f:
        f.write(f"Matched: {len(matched)}/{len(drug_results)}\n")
        f.write("-" * 40 + "\n")
        for r in drug_results:
            mark = "✅" if r["status"] == "matched" else "  "
            src = r.get("source") or "-"
            f.write(
                f"{mark} [{src:8s}][{r['score']:.2f}] "
                f"{r['ocr_text'][:40]:40s}"
                f" → {r['matched_drug'] or '-'}\n"
            )

    elapsed = time.time() - t0
    summary = {
        "image": stem,
        "time_s": round(elapsed, 1),
        "ocr_blocks": len(result.text_blocks),
        "grouped": len(grouped),
        "drugs_matched": len(matched),
        "drugs_total": len(drug_results),
        "matched_names": matched,
        "prep": prep_info,
    }

    # Summary per-image
    with open(os.path.join(out_dir, "summary.txt"),
              "w", encoding="utf-8") as f:
        f.write(f"Image:   {stem}\n")
        f.write(f"Time:    {elapsed:.1f}s\n")
        f.write(f"OCR:     {len(result.text_blocks)} blocks\n")
        f.write(f"Grouped: {len(grouped)} blocks\n")
        f.write(f"Drugs:   {len(matched)}/{len(drug_results)} matched\n")
        f.write(f"Matches: {matched}\n")

    logger.info(
        f"[{stem}] Done {elapsed:.1f}s | "
        f"OCR={len(result.text_blocks)} | "
        f"Drugs={len(matched)}/{len(drug_results)}"
    )
    return summary


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs="+", default=None)
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()

    # Default image list
    if args.images:
        images = args.images
    else:
        images = sorted([
            str(p) for p in Path("data/input").glob("*.jpg")
        ])

    if not images:
        logger.error("No images found in data/input/")
        sys.exit(1)

    # Clean old batch output
    if os.path.isdir(BATCH_DIR):
        shutil.rmtree(BATCH_DIR)
    os.makedirs(BATCH_DIR)
    logger.info(f"Processing {len(images)} images → {BATCH_DIR}/")

    # ── Singleton: load OCR + DrugLookup once ─────────────────────────────
    from core.ocr.ocr_engine import HybridOcrModule
    from core.converter.drug_lookup import DrugLookup

    device = "cuda" if args.gpu else "cpu"
    logger.info(f"Loading OCR engine (singleton, device={device})...")
    ocr = HybridOcrModule(device=device)
    drug_lu = DrugLookup()

    # YOLO detector (singleton)
    from core.detector import PrescriptionDetector
    yolo = PrescriptionDetector()
    logger.info("Models loaded — starting batch.")

    all_summaries = []
    t_total = time.time()

    for i, img_path in enumerate(images):
        stem = Path(img_path).stem
        out_dir = os.path.join(BATCH_DIR, stem)
        logger.info(f"\n[{i+1}/{len(images)}] {stem}")
        try:
            s = process_image(
                img_path, out_dir,
                ocr_module=ocr,
                drug_lookup=drug_lu,
                detector=yolo,
                use_gpu=args.gpu,
            )
        except Exception as e:
            logger.error(f"  Error: {e}")
            s = {"image": stem, "error": str(e)}
        all_summaries.append(s)

    # Global summary
    total = time.time() - t_total
    print("\n" + "=" * 60)
    print(f"  BATCH SUMMARY — {len(images)} images, {total:.0f}s total")
    print("=" * 60)
    for s in all_summaries:
        if "error" in s:
            print(f"  ❌ {s['image']}: {s['error']}")
        else:
            print(
                f"  {s['image']}: "
                f"OCR={s['ocr_blocks']} | "
                f"Drugs={s['drugs_matched']}/{s['drugs_total']} | "
                f"{s['time_s']}s"
            )
            if s["matched_names"]:
                for name in s["matched_names"]:
                    print(f"      → {name}")
    print("=" * 60)
    print(f"📂 {os.path.abspath(BATCH_DIR)}/")

    # Save global summary JSON
    with open(os.path.join(BATCH_DIR, "batch_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

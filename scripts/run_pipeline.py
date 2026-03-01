"""
run_pipeline.py — MedicineApp unified pipeline.

Phase A (quét đơn thuốc):
  1. YOLO detect + crop
  2. Preprocess (deskew, orientation)
  3. OCR (PaddleOCR + VietOCR)
  4. Grouping (merge same-line + group drug lines)
  5. GCN classify drugname/other
  6. Drug search (Drug Lookup DB)

Phase B (xác minh thuốc — optional):
  7. FRCNN detect pills
  8. GCN + Contrastive matching

Usage:
  # Phase A only (1 image)
  python scripts/run_pipeline.py --image data/input/IMG_20260209_180420.jpg

  # Phase A on all images
  python scripts/run_pipeline.py --all

  # Phase A + B (with pill image)
  python scripts/run_pipeline.py --image data/input/IMG_XXX.jpg --pill data/pills/test/pill.jpg
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import cv2

# Setup
ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, ROOT)
os.environ.setdefault("FLAGS_enable_pir_api", "0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("pipeline")

MAX_DIM = 1600
OUTPUT_DIR = os.path.join(ROOT, "output", "pipeline")


# ── Helpers ──────────────────────────────────────────────────────────────────

def resize_if_needed(img):
    h, w = img.shape[:2]
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    return img


def print_header(text, char="═"):
    line = char * 60
    print(f"\n{line}")
    print(f"  {text}")
    print(f"{line}")


def print_step(num, name, status, time_s=None, detail=""):
    icon = "✅" if status == "ok" else ("⏭" if status == "skip" else "❌")
    time_str = f" {time_s:.1f}s" if time_s is not None else ""
    det_str = f"  ({detail})" if detail else ""
    print(f"  ▸ Step {num}: {name:.<30s} {icon}{time_str}{det_str}")


# ── Per-image pipeline ───────────────────────────────────────────────────────

def run_phase_a(img_path, out_dir, shared=None):
    """
    Phase A: Quét đơn thuốc.
    Returns (summary_dict, ocr_blocks_with_bbox)
    """
    os.makedirs(out_dir, exist_ok=True)
    stem = Path(img_path).stem
    t_total = time.time()
    summary = {"image": stem, "steps": {}}

    # ── Step 1: YOLO detect + crop ────────────────────────────────────────
    t0 = time.time()
    img = cv2.imread(img_path)
    if img is None:
        print_step(1, "YOLO Detect", "fail", detail="Cannot read image")
        return {"image": stem, "error": "cannot_read"}, []

    cv2.imwrite(os.path.join(out_dir, "step-0_raw.jpg"), img)

    detector = shared.get("detector") if shared else None
    if detector is not None:
        from core.segmentation import crop_by_mask
        yolo_results = detector.predict(img)
        if yolo_results and yolo_results[0].masks is not None:
            cropped = crop_by_mask(img, yolo_results[0])
            if cropped is not None:
                img = cropped
        crop_info = f"cropped {img.shape[1]}×{img.shape[0]}"
    else:
        crop_info = f"raw {img.shape[1]}×{img.shape[0]}"

    cv2.imwrite(os.path.join(out_dir, "step-1_cropped.jpg"), img)
    t1 = time.time() - t0
    print_step(1, "YOLO Detect", "ok", t1, crop_info)
    summary["steps"]["yolo"] = {"time_s": round(t1, 1), "detail": crop_info}

    # ── Step 2: Preprocess ────────────────────────────────────────────────
    t0 = time.time()
    from core.preprocessor.orientation import preprocess_image
    processed, prep_info = preprocess_image(img, stem="step-2", save_dir=out_dir)
    processed = resize_if_needed(processed)
    cv2.imwrite(os.path.join(out_dir, "step-2_preprocessed.jpg"), processed)
    t2 = time.time() - t0
    orient = prep_info.get("rotation", "0°")
    print_step(2, "Preprocess", "ok", t2, f"orient={orient}")
    summary["steps"]["preprocess"] = {"time_s": round(t2, 1), "info": prep_info}

    # ── Step 3: OCR ───────────────────────────────────────────────────────
    t0 = time.time()
    ocr_module = shared.get("ocr") if shared else None
    if ocr_module is None:
        from core.ocr.ocr_engine import HybridOcrModule
        ocr_module = HybridOcrModule(device="cpu")
        if shared is not None:
            shared["ocr"] = ocr_module

    result = ocr_module.extract(processed, input_type="raw")
    ocr_module.save_results(result, processed, "step-3", out_dir, out_dir, out_dir)

    ocr_blocks = [
        {
            "text": b.text,
            "confidence": round(b.confidence, 4),
            "bbox": b.bbox,
        }
        for b in result.text_blocks
    ]
    ocr_json = {
        "module": result.module_name,
        "elapsed_ms": result.elapsed_ms,
        "block_count": len(ocr_blocks),
        "blocks": ocr_blocks,
    }
    with open(os.path.join(out_dir, "step-3_ocr.json"), "w", encoding="utf-8") as f:
        json.dump(ocr_json, f, ensure_ascii=False, indent=2)

    t3 = time.time() - t0
    print_step(3, "OCR", "ok", t3, f"{len(ocr_blocks)} text blocks")
    summary["steps"]["ocr"] = {"time_s": round(t3, 1), "blocks": len(ocr_blocks)}

    # ── Step 4: Grouping ──────────────────────────────────────────────────
    t0 = time.time()
    from core.converter.ocr_to_pima import OcrToPimaConverter
    same_line = OcrToPimaConverter.merge_same_line_blocks(ocr_blocks)
    grouped = OcrToPimaConverter.group_drug_lines(same_line)

    grouped_json = {
        "raw_count": len(ocr_blocks),
        "after_same_line": len(same_line),
        "after_grouping": len(grouped),
        "blocks": [{"text": b.get("text", ""), "label": b.get("label", ""), "bbox": b.get("bbox", [])} for b in grouped],
    }
    with open(os.path.join(out_dir, "step-4_grouped.json"), "w", encoding="utf-8") as f:
        json.dump(grouped_json, f, ensure_ascii=False, indent=2)

    t4 = time.time() - t0
    detail = f"{len(ocr_blocks)}→{len(same_line)}→{len(grouped)}"
    print_step(4, "Grouping", "ok", t4, detail)
    summary["steps"]["grouping"] = {
        "time_s": round(t4, 1),
        "raw": len(ocr_blocks),
        "same_line": len(same_line),
        "grouped": len(grouped),
    }

    # ── Step 5: GCN Classify drugname/other ───────────────────────────────
    t0 = time.time()
    matcher = shared.get("matcher") if shared else None
    gcn_ok = False
    gcn_results = []

    if matcher is not None:
        try:
            gcn_results = matcher.classify_prescription(grouped, img_w=1000, img_h=1000)
            gcn_ok = True
        except Exception as e:
            logger.warning(f"GCN classify failed: {e}")

    if not gcn_ok:
        # Fallback: try loading matcher
        try:
            from core.matcher import ZeroPimaMatcher
            if matcher is None:
                matcher = ZeroPimaMatcher()
                if shared is not None:
                    shared["matcher"] = matcher
            gcn_results = matcher.classify_prescription(grouped, img_w=1000, img_h=1000)
            gcn_ok = True
        except Exception as e:
            logger.warning(f"GCN not available: {e}")
            # Fallback: use DrugLookup heuristics
            gcn_results = []
            for b in grouped:
                gcn_results.append({
                    "text": b.get("text", ""),
                    "label": "unknown",
                    "confidence": 0.0,
                    "bbox": b.get("bbox", []),
                })

    # Separate drugnames
    drug_names = [r for r in gcn_results if r["label"] == "drugname"]

    with open(os.path.join(out_dir, "step-5_gcn_classify.json"), "w", encoding="utf-8") as f:
        json.dump(gcn_results, f, ensure_ascii=False, indent=2)

    t5 = time.time() - t0
    method = "GCN" if gcn_ok else "fallback"
    print_step(5, "GCN Classify", "ok" if gcn_ok else "skip", t5,
               f"{len(drug_names)} drugnames ({method})")
    summary["steps"]["gcn_classify"] = {
        "time_s": round(t5, 1),
        "method": method,
        "drugnames": len(drug_names),
        "total": len(gcn_results),
    }

    # Print detected drug names
    for r in gcn_results:
        icon = "💊" if r["label"] == "drugname" else "  "
        conf = f"[{r['confidence']:.0%}]" if r["confidence"] > 0 else ""
        print(f"      {icon} {r['text'][:50]} {conf}")

    # ── Step 6: Drug Search ───────────────────────────────────────────────
    t0 = time.time()
    drug_lookup = shared.get("drug_lookup") if shared else None
    if drug_lookup is None:
        from core.converter.drug_lookup import DrugLookup
        drug_lookup = DrugLookup()
        if shared is not None:
            shared["drug_lookup"] = drug_lookup

    SKIP_PATTERNS = {
        "bộ y tế", "đơn thuốc", "điện thoại", "họ tên", "tuổi",
        "giới tính", "mã số", "bhyt", "địa chỉ", "chẩn đoán",
        "chấn đoán", "stt", "thuốc điều trị", "van co",
        "văn cơ", "bvđk", "bệnh viện",
    }
    MIN_DRUG_SCORE = 0.3

    drug_results = []
    matched_drugs = []

    # Search from GCN-classified drugnames (or all blocks if no GCN)
    search_blocks = drug_names if drug_names else grouped
    for b in search_blocks:
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
            matched_drugs.append(r["name"])

    with open(os.path.join(out_dir, "step-6_drug_search.json"), "w", encoding="utf-8") as f:
        json.dump(drug_results, f, ensure_ascii=False, indent=2)

    t6 = time.time() - t0
    print_step(6, "Drug Search", "ok", t6, f"{len(matched_drugs)}/{len(drug_results)} matched")

    if matched_drugs:
        for name in matched_drugs:
            print(f"      → {name}")

    summary["steps"]["drug_search"] = {
        "time_s": round(t6, 1),
        "matched": len(matched_drugs),
        "total": len(drug_results),
        "drugs": matched_drugs,
    }

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - t_total
    summary["total_time_s"] = round(elapsed, 1)
    summary["drugs_found"] = matched_drugs

    # Save summary
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"  {'─' * 56}")
    print(f"  Total: {elapsed:.1f}s | Drugs found: {len(matched_drugs)}")

    return summary, grouped


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MedicineApp Pipeline")
    parser.add_argument("--image", type=str, help="Single image path")
    parser.add_argument("--all", action="store_true", help="Process all images in data/input/")
    parser.add_argument("--pill", type=str, default=None, help="Pill image for Phase B")
    parser.add_argument("--gpu", action="store_true", help="Use GPU")
    parser.add_argument("--no-gcn", action="store_true", help="Skip GCN, use DrugLookup only")
    args = parser.parse_args()

    # Determine images to process
    if args.image:
        images = [args.image]
    elif args.all:
        input_dir = os.path.join(ROOT, "data", "input")
        images = sorted([str(p) for p in Path(input_dir).glob("*.jpg")])
    else:
        # Default: first image
        input_dir = os.path.join(ROOT, "data", "input")
        images = sorted([str(p) for p in Path(input_dir).glob("*.jpg")])[:1]

    if not images:
        logger.error("No images found!")
        sys.exit(1)

    # ── Load shared modules (singleton) ────────────────────────────────────
    shared = {}

    # YOLO detector
    print_header("Loading Models")
    t0 = time.time()

    from core.detector import PrescriptionDetector
    shared["detector"] = PrescriptionDetector()
    print(f"  YOLO detector loaded")

    # Zero-PIMA GCN matcher (lazy loaded in step 5)
    if not args.no_gcn:
        try:
            from core.matcher import ZeroPimaMatcher
            matcher = ZeroPimaMatcher()
            # Pre-load to measure time
            _ = matcher.checkpoint_info
            shared["matcher"] = matcher
            print(f"  Zero-PIMA GCN loaded (epoch={matcher.checkpoint_info['epoch']}, "
                  f"loss={matcher.checkpoint_info['loss']:.4f})")
        except Exception as e:
            logger.warning(f"Zero-PIMA not available: {e}. Using DrugLookup fallback.")

    print(f"  Models loaded in {time.time()-t0:.1f}s")

    # ── Process images ────────────────────────────────────────────────────
    all_summaries = []
    t_all = time.time()

    for i, img_path in enumerate(images):
        stem = Path(img_path).stem
        out_dir = os.path.join(OUTPUT_DIR, stem)

        print_header(f"MedicineApp Pipeline — [{i+1}/{len(images)}] {stem}")

        try:
            summary, grouped = run_phase_a(img_path, out_dir, shared=shared)
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            summary = {"image": stem, "error": str(e)}
            grouped = []

        all_summaries.append(summary)

    # ── Final Summary ─────────────────────────────────────────────────────
    total_time = time.time() - t_all
    print_header(f"SUMMARY — {len(images)} images, {total_time:.0f}s total")

    for s in all_summaries:
        if "error" in s:
            print(f"  ❌ {s['image']}: {s['error']}")
        else:
            drugs = s.get("drugs_found", [])
            t = s.get("total_time_s", 0)
            print(f"  {s['image']}: {t:.1f}s | Drugs: {len(drugs)}")
            for d in drugs:
                print(f"      → {d}")

    print(f"\n  📂 Output: {os.path.abspath(OUTPUT_DIR)}/")

    # Save batch summary
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "batch_summary.json"), "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

"""
run_pipeline.py — MedicineApp unified pipeline.

Phase A (quét đơn thuốc — 4 bước):
  1. YOLO detect + crop
  2. Preprocess (deskew, orientation)
  3. OCR (PaddleOCR detect + VietOCR recognize)
  4. NER classify drugname/other (PhoBERT)

Phase B (xác minh thuốc — chưa hoạt động):
  7. FRCNN detect pills
  8. GCN contrastive matching

Usage:
  python scripts/run_pipeline.py --image data/input/IMG.jpg
  python scripts/run_pipeline.py --all
  python scripts/run_pipeline.py --dir data/input/prescription_3
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

MAX_DIM = 1200
OUTPUT_DIR = os.path.join(ROOT, "data", "output", "phase_a")


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
        from core.phase_a.s1_detect.segmentation import crop_by_mask
        yolo_results = detector.predict(img)
        if yolo_results and yolo_results[0].masks is not None:
            cropped, offset = crop_by_mask(img, yolo_results[0])
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
    from core.phase_a.s2_preprocess.orientation import preprocess_image
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
        from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule
        import torch
        _ocr_device = "gpu" if torch.cuda.is_available() else "cpu"
        ocr_module = HybridOcrModule(device=_ocr_device)
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

    # ── Build NER input from OCR blocks ──────────────────────────────────
    ner_input = []
    for b in ocr_blocks:
        text = b.get("text", "").strip()
        if not text:
            continue
        ner_input.append({
            "text": text,
            "label": "other",
            "box": [0, 0, 0, 0],
            "bbox": b.get("bbox", []),
        })

    # ── Step 4: NER Classify drugname/other ───────────────────────────────
    t0 = time.time()
    matcher = shared.get("matcher") if shared else None

    if matcher is not None:
        ner_results = matcher.classify(ner_input)
    else:
        from core.phase_a.s5_classify.ner_extractor import NerExtractor
        matcher = NerExtractor()
        if shared is not None:
            shared["matcher"] = matcher
        ner_results = matcher.classify(ner_input)

    # Post-NER filter: dosage/instruction text → force "other"
    import re as _re
    _DOSAGE_RE = _re.compile(
        r"(uống|ngày\s+\d|lần\s*,|sau\s*ăn|trước\s*ăn|"
        r"sáng\s+uống|trưa\s+uống|tối\s+uống|"
        r"mỗi\s+lần|hòa\s+tan|nhỏ\s+mắt)",
        _re.IGNORECASE,
    )
    _PURE_NUM_RE = _re.compile(r"^[\d\s.,]+$")
    # "Viên 60 8", "Viên 15", "Ống 20", "Tab 30 5"
    _UNIT_ONLY_RE = _re.compile(
        r"^(viên|ống|lọ|tab|gói|viên\s+sủi)\s+[\d\s]*$",
        _re.IGNORECASE,
    )
    # "20 50mg", "150mg", "500mcg"
    _DOSAGE_ONLY_RE = _re.compile(
        r"^[\d\s.,]*(mg|ml|mcg|g|iu)\b",
        _re.IGNORECASE,
    )
    # Non-drug: headers, hospital names, dates, addresses
    _HEADER_RE = _re.compile(
        r"(đơn\s+thuốc|bhyt|bệnh\s+viện|phòng\s+khám|"
        r"họ\s+tên|giới\s+tính|địa\s+chỉ|chẩn\s+đoán|"
        r"thuốc\s+điều\s+trị|mã\s+số|số\s+phiếu|"
        r"bộ\s+y\s+tế|sở\s+y\s+tế|xem\s+tiếp)",
        _re.IGNORECASE,
    )
    for r in ner_results:
        if r["label"] == "drugname":
            txt = r["text"].strip()
            if (_DOSAGE_RE.search(txt) or
                    _PURE_NUM_RE.match(txt) or
                    _UNIT_ONLY_RE.match(txt) or
                    _DOSAGE_ONLY_RE.match(txt) or
                    _HEADER_RE.search(txt) or
                    len(txt) < 4):
                r["label"] = "other"
                r["confidence"] = 0.0

    # Separate drugnames
    drug_names = [r for r in ner_results if r["label"] == "drugname"]

    with open(os.path.join(out_dir, "step-4_ner_classify.json"), "w", encoding="utf-8") as f:
        json.dump(ner_results, f, ensure_ascii=False, indent=2)

    t5 = time.time() - t0
    print_step(4, "NER Classify", "ok", t5,
               f"{len(drug_names)} drugnames")
    summary["steps"]["ner_classify"] = {
        "time_s": round(t5, 1),
        "method": "PhoBERT-NER",
        "drugnames": len(drug_names),
        "total": len(ner_results),
    }

    # Print all blocks — highlight drugnames
    for r in ner_results:
        icon = "💊" if r["label"] == "drugname" else "  "
        conf = f"[{r['confidence']:.0%}]" if r["confidence"] > 0 else ""
        print(f"      {icon} {r['text'][:60]} {conf}")

    # ── Summary ───────────────────────────────────────────────────────────
    extracted_names = [r["text"] for r in drug_names]

    elapsed = time.time() - t_total
    summary["total_time_s"] = round(elapsed, 1)
    summary["drugs_found"] = extracted_names

    # Save summary
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"  {'─' * 56}")
    print(f"  Total: {elapsed:.1f}s | Drugs found: {len(extracted_names)}")
    for name in extracted_names:
        print(f"      💊 {name}")

    return summary, ner_input


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MedicineApp Pipeline")
    parser.add_argument("--image", type=str, help="Single image path")
    parser.add_argument("--dir", type=str, help="Directory of images to process")
    parser.add_argument("--all", action="store_true", help="Process all images in data/input/")
    parser.add_argument("--pill", type=str, default=None, help="Pill image for Phase B")
    parser.add_argument("--gpu", action="store_true", help="Use GPU")
    parser.add_argument("--no-ner", action="store_true", help="Skip NER, use DrugLookup only")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of images to process")
    args = parser.parse_args()

    # Determine images to process
    if args.image:
        images = [args.image]
    elif args.dir:
        img_dir = Path(args.dir)
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        images = sorted([
            str(p) for p in img_dir.iterdir()
            if p.suffix.lower() in exts
        ])
    elif args.all:
        input_dir = os.path.join(ROOT, "data", "input")
        images = sorted([
            str(p) for p in Path(input_dir).rglob("*")
            if p.suffix.lower() in (".jpg", ".jpeg", ".png")
        ])
    else:
        # Default: first image in any subfolder
        input_dir = os.path.join(ROOT, "data", "input")
        images = sorted([
            str(p) for p in Path(input_dir).rglob("*")
            if p.suffix.lower() in (".jpg", ".jpeg", ".png")
        ])[:1]

    if args.limit and args.limit > 0:
        images = images[:args.limit]

    if not images:
        logger.error("No images found!")
        sys.exit(1)

    # ── Load shared modules (singleton) ────────────────────────────────────
    shared = {}

    # YOLO detector
    print_header("Loading Models")
    t0 = time.time()

    from core.phase_a.s1_detect.detector import PrescriptionDetector
    shared["detector"] = PrescriptionDetector()
    print("  YOLO detector loaded")

    # PhoBERT NER matcher
    if not args.no_ner:
        try:
            from core.phase_a.s5_classify.ner_extractor import NerExtractor
            matcher = NerExtractor()
            shared["matcher"] = matcher
            print("  PhoBERT NER loaded (F1=100%)")
        except Exception as e:
            logger.warning(f"NER not available: {e}. Using DrugLookup fallback.")

    print(f"  Models loaded in {time.time()-t0:.1f}s")

    # ── Process images ────────────────────────────────────────────────────
    all_summaries = []
    t_all = time.time()

    for i, img_path in enumerate(images):
        stem = Path(img_path).stem
        out_dir = os.path.join(OUTPUT_DIR, stem)

        print_header(f"MedicineApp Pipeline — [{i+1}/{len(images)}] {stem}")

        try:
            summary, _ = run_phase_a(img_path, out_dir, shared=shared)
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            summary = {"image": stem, "error": str(e)}

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
                print(f"      💊 {d}")

    # ── Consensus Voting (multi-image) ────────────────────────────────────
    consensus_results = []
    if len(images) >= 2:
        consensus_results = _consensus_vote(
            OUTPUT_DIR, all_summaries
        )

    print(f"\n  📂 Output: {os.path.abspath(OUTPUT_DIR)}/")

    # Save batch summary
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    batch = {
        "summaries": all_summaries,
        "consensus": consensus_results,
    }
    with open(
        os.path.join(OUTPUT_DIR, "batch_summary.json"),
        "w", encoding="utf-8",
    ) as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)


def _consensus_vote(output_dir, summaries, threshold=0.6,
                    min_images=2, min_text_len=5):
    """Cross-image consensus voting for drug names.

    Collects all NER drugname predictions, groups similar
    texts via fuzzy matching, keeps only those appearing
    in >= min_images.

    Returns list of consensus drug dicts.
    """
    from difflib import SequenceMatcher
    from collections import Counter

    # Collect all drugname blocks
    all_drugs = []
    for s in summaries:
        if "error" in s:
            continue
        img = s.get("image", "")
        ner_path = os.path.join(
            output_dir, img, "step-4_ner_classify.json"
        )
        if not os.path.isfile(ner_path):
            continue
        with open(ner_path, encoding="utf-8") as f:
            ner = json.load(f)
        for b in ner:
            if b["label"] == "drugname":
                text = b["text"].strip()
                if len(text) >= min_text_len:
                    all_drugs.append({
                        "image": img,
                        "text": text,
                        "conf": b["confidence"],
                    })

    if not all_drugs:
        return []

    # Cluster similar texts
    clusters = []
    for d in all_drugs:
        placed = False
        for cluster in clusters:
            rep = cluster[0]["text"]
            sim = SequenceMatcher(
                None, d["text"].lower(), rep.lower()
            ).ratio()
            if sim >= threshold:
                cluster.append(d)
                placed = True
                break
        if not placed:
            clusters.append([d])

    # Vote: keep clusters with >= min_images
    results = []
    for cluster in clusters:
        images = set(d["image"] for d in cluster)
        if len(images) < min_images:
            continue
        texts = Counter(d["text"] for d in cluster)
        best_text, best_count = texts.most_common(1)[0]
        avg_conf = sum(
            d["conf"] for d in cluster
        ) / len(cluster)
        results.append({
            "drug_name": best_text,
            "votes": best_count,
            "total_images": len(images),
            "avg_confidence": round(avg_conf, 2),
            "variants": list(set(d["text"] for d in cluster)),
        })

    results.sort(
        key=lambda x: x["total_images"], reverse=True
    )

    # Print
    if results:
        print(f"\n  {'─' * 56}")
        print(f"  CONSENSUS ({len(images)} images,"
              f" threshold={threshold}):")
        for r in results:
            print(f"      💊 {r['drug_name'][:55]}"
                  f"  [{r['votes']}/{r['total_images']}]")
    else:
        print(f"\n  No consensus drugs"
              f" (need >= {min_images} images)")

    # Save
    consensus_path = os.path.join(
        output_dir, "consensus_drugs.json"
    )
    with open(consensus_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


if __name__ == "__main__":
    main()

"""
scripts/benchmark_vaipe_end2end.py — VAIPE In-Domain End-to-End Diagnostic Evaluation.

Evaluates the real Android ML Kit OCR output on VAIPE prescription images
across 4 pipeline stages using:
- Production PhoBERT NER model (models/phobert_ner_model)
- Production DrugLookup (data/drug_db_vn_full.json)
- Real ML Kit OCR JSONs from Android device (reports/vaipe_mlkit_end2end/mlkit_ocr/)
- VAIPE canonical ground truth (vaipe-p/public_train/label/)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.pipeline import MedicinePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VAIpeEnd2End")


def normalize_text(text: Optional[str]) -> str:
    """Normalize Unicode (NFC), lowercase, remove punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def extract_gold_drugs_from_vaipe_label(label_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract gold drugname entities from VAIPE label JSON."""
    gold_drugs = []
    for item in label_data:
        if item.get("label") == "drugname":
            raw_text = item.get("text", "").strip()
            # Strip STT prefix like "1) ", "1. ", "① " if present
            clean_text = re.sub(r"^(\d+[\.\/\),-:]|[①-⑩]|STT\s*[:.]?\s*\d+)\s*", "", raw_text, flags=re.IGNORECASE).strip()
            norm_text = normalize_text(clean_text)
            if norm_text:
                gold_drugs.append({
                    "id": item.get("id"),
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "normalized": norm_text,
                    "box": item.get("box"),
                    "mapping": item.get("mapping"),
                })
    return gold_drugs


def check_drug_match(
    candidate_name: str,
    matched_drug_name: Optional[str],
    gold_drug: dict[str, Any],
) -> bool:
    """Check if candidate drug matches gold drug via strict or normalized token overlap."""
    norm_cand = normalize_text(candidate_name)
    norm_matched = normalize_text(matched_drug_name)
    norm_gold = gold_drug["normalized"]

    if norm_cand == norm_gold or norm_matched == norm_gold:
        return True

    # Check significant token containment (>= 4 chars or token match)
    gold_tokens = [t for t in norm_gold.split() if len(t) >= 3]
    if gold_tokens:
        primary_gold_token = gold_tokens[0]
        if primary_gold_token in norm_cand.split() or primary_gold_token in norm_matched.split():
            return True

    if len(norm_gold) >= 4 and (norm_gold in norm_cand or norm_cand in norm_gold):
        return True

    return False


def run_vaipe_benchmark(
    ocr_dir: Path,
    gt_dir: Path,
    output_dir: Path,
    limit: Optional[int] = None,
):
    """Run 4-stage evaluation on VAIPE ML Kit OCR captures."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ocr_files = sorted(list(ocr_dir.glob("*.json")))
    if not ocr_files:
        logger.error(f"No OCR JSON files found in {ocr_dir.resolve()}. Please run device OCR first.")
        return

    if limit:
        ocr_files = ocr_files[:limit]

    logger.info(f"Found {len(ocr_files)} OCR JSON files to evaluate.")

    pipe = MedicinePipeline()

    per_image_records = []
    ocr_coverage_records = []
    ner_predictions = []
    lookup_predictions = []
    error_examples = []

    # Overall metrics accumulators
    total_gold_drugs = 0
    total_ocr_hits = 0
    total_ner_tp = 0
    total_ner_fp = 0
    total_lookup_tp = 0
    total_lookup_fp = 0
    total_confirmed_lookup = 0

    taxonomy_counts = defaultdict(int)

    for file_idx, ocr_file in enumerate(ocr_files):
        with open(ocr_file, "r", encoding="utf-8") as f:
            ocr_data = json.load(f)

        image_id = ocr_data.get("image_id") or ocr_file.stem
        raw_full_text = ocr_data.get("text", "")
        norm_full_ocr = normalize_text(raw_full_text)
        lines = ocr_data.get("lines", [])

        # Load GT
        gt_file = gt_dir / f"{image_id}.json"
        if not gt_file.exists():
            logger.warning(f"GT file not found: {gt_file.name}, skipping.")
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        gold_drugs = extract_gold_drugs_from_vaipe_label(gt_data)
        num_gold = len(gold_drugs)
        total_gold_drugs += num_gold

        # Stage 1: OCR Coverage
        ocr_hits = 0
        gold_ocr_status = {}
        for g in gold_drugs:
            norm_g = g["normalized"]
            g_tokens = [t for t in norm_g.split() if len(t) >= 3]
            primary_token = g_tokens[0] if g_tokens else norm_g
            found_in_ocr = norm_g in norm_full_ocr or primary_token in norm_full_ocr
            gold_ocr_status[g["id"]] = found_in_ocr
            if found_in_ocr:
                ocr_hits += 1
            ocr_coverage_records.append({
                "image_id": image_id,
                "gold_id": g["id"],
                "gold_raw": g["raw_text"],
                "gold_clean": g["clean_text"],
                "found_in_ocr": found_in_ocr,
            })
        total_ocr_hits += ocr_hits
        ocr_cov_rate = ocr_hits / num_gold if num_gold > 0 else 0.0

        # Stage 2 & 3: Run pipeline with P0 strategy (primary)
        res = pipe.scan_prescription_app(
            ocr_lines=lines,
            ocr_text=raw_full_text,
            layout_strategy="p0_raw_text",
        )
        extracted_meds = res.get("medications", [])

        # Match NER predictions with GT
        matched_gold_ner = set()
        matched_gold_lookup = set()
        img_ner_tp = 0
        img_ner_fp = 0
        img_lookup_tp = 0
        img_lookup_fp = 0
        img_confirmed = 0

        for m in extracted_meds:
            dname = m.get("drug_name", "") or m.get("ocr_text", "")
            mname = m.get("matched_drug_name")
            status = m.get("mapping_status")
            score = float(m.get("match_score", 0.0))

            # Check NER match
            matched_gold_item = None
            for g in gold_drugs:
                if check_drug_match(dname, mname, g):
                    matched_gold_item = g
                    break

            if matched_gold_item:
                gid = matched_gold_item["id"]
                if gid not in matched_gold_ner:
                    matched_gold_ner.add(gid)
                    img_ner_tp += 1
                if gid not in matched_gold_lookup and (status in ("confirmed", "unmapped_candidate") and (score >= 0.7 or mname)):
                    matched_gold_lookup.add(gid)
                    img_lookup_tp += 1
                    if status == "confirmed":
                        img_confirmed += 1
            else:
                img_ner_fp += 1
                img_lookup_fp += 1

            ner_predictions.append({
                "image_id": image_id,
                "drug_name": dname,
                "is_match": bool(matched_gold_item),
            })
            lookup_predictions.append({
                "image_id": image_id,
                "drug_name": dname,
                "matched_drug_name": mname,
                "mapping_status": status,
                "score": score,
            })

        total_ner_tp += img_ner_tp
        total_ner_fp += img_ner_fp
        total_lookup_tp += img_lookup_tp
        total_lookup_fp += img_lookup_fp
        total_confirmed_lookup += img_confirmed

        # Cascade failure classification for each gold drug
        for g in gold_drugs:
            gid = g["id"]
            if not gold_ocr_status.get(gid, False):
                taxonomy_counts["OCR_MISS"] += 1
                if len(error_examples) < 15:
                    error_examples.append({
                        "image_id": image_id,
                        "gold_drug": g["clean_text"],
                        "failure_stage": "OCR_MISS",
                        "reason": "Text not detected in ML Kit OCR output",
                    })
            elif gid not in matched_gold_ner:
                taxonomy_counts["NER_MISS"] += 1
                if len(error_examples) < 15:
                    error_examples.append({
                        "image_id": image_id,
                        "gold_drug": g["clean_text"],
                        "failure_stage": "NER_MISS",
                        "reason": "Present in OCR but PhoBERT NER did not classify as drugname",
                    })
            elif gid not in matched_gold_lookup:
                taxonomy_counts["LOOKUP_MISS"] += 1
                if len(error_examples) < 15:
                    error_examples.append({
                        "image_id": image_id,
                        "gold_drug": g["clean_text"],
                        "failure_stage": "LOOKUP_MISS",
                        "reason": "Extracted by NER but DrugLookup score < 0.7",
                    })
            else:
                taxonomy_counts["SUCCESS"] += 1

        ner_rec = img_ner_tp / num_gold if num_gold > 0 else 0.0
        ner_prec = img_ner_tp / (img_ner_tp + img_ner_fp) if (img_ner_tp + img_ner_fp) > 0 else 0.0
        lookup_rec = img_lookup_tp / num_gold if num_gold > 0 else 0.0

        per_image_records.append({
            "image_id": image_id,
            "gold_count": num_gold,
            "ocr_hits": ocr_hits,
            "ocr_coverage": round(ocr_cov_rate, 4),
            "ner_tp": img_ner_tp,
            "ner_fp": img_ner_fp,
            "ner_precision": round(ner_prec, 4),
            "ner_recall": round(ner_rec, 4),
            "lookup_tp": img_lookup_tp,
            "lookup_recall": round(lookup_rec, 4),
            "confirmed_count": img_confirmed,
        })

    # Summary calculations across 4 stages
    ocr_cov_macro = sum(r["ocr_coverage"] for r in per_image_records) / max(1, len(per_image_records))
    ocr_cov_micro = total_ocr_hits / total_gold_drugs if total_gold_drugs > 0 else 0.0

    ner_micro_p = total_ner_tp / (total_ner_tp + total_ner_fp) if (total_ner_tp + total_ner_fp) > 0 else 0.0
    ner_micro_r = total_ner_tp / total_gold_drugs if total_gold_drugs > 0 else 0.0
    ner_micro_f1 = (2 * ner_micro_p * ner_micro_r) / (ner_micro_p + ner_micro_r) if (ner_micro_p + ner_micro_r) > 0 else 0.0

    lookup_micro_p = total_lookup_tp / (total_lookup_tp + total_lookup_fp) if (total_lookup_tp + total_lookup_fp) > 0 else 0.0
    lookup_micro_r = total_lookup_tp / total_gold_drugs if total_gold_drugs > 0 else 0.0
    lookup_micro_f1 = (2 * lookup_micro_p * lookup_micro_r) / (lookup_micro_p + lookup_micro_r) if (lookup_micro_p + lookup_micro_r) > 0 else 0.0

    summary_rows = [
        {
            "stage": "1. ML Kit OCR Coverage",
            "precision": "-",
            "recall": f"{ocr_cov_micro*100:.2f}%",
            "f1": "-",
            "tp": total_ocr_hits,
            "fp": 0,
            "fn": total_gold_drugs - total_ocr_hits,
            "total_gold": total_gold_drugs,
        },
        {
            "stage": "2. Old PhoBERT NER after ML Kit",
            "precision": f"{ner_micro_p*100:.2f}%",
            "recall": f"{ner_micro_r*100:.2f}%",
            "f1": f"{ner_micro_f1*100:.2f}%",
            "tp": total_ner_tp,
            "fp": total_ner_fp,
            "fn": total_gold_drugs - total_ner_tp,
            "total_gold": total_gold_drugs,
        },
        {
            "stage": "3. + DrugLookup Resolution",
            "precision": f"{lookup_micro_p*100:.2f}%",
            "recall": f"{lookup_micro_r*100:.2f}%",
            "f1": f"{lookup_micro_f1*100:.2f}%",
            "tp": total_lookup_tp,
            "fp": total_lookup_fp,
            "fn": total_gold_drugs - total_lookup_tp,
            "total_gold": total_gold_drugs,
        },
        {
            "stage": "4. Final End-to-End Pipeline",
            "precision": f"{lookup_micro_p*100:.2f}%",
            "recall": f"{lookup_micro_r*100:.2f}%",
            "f1": f"{lookup_micro_f1*100:.2f}%",
            "tp": total_lookup_tp,
            "fp": total_lookup_fp,
            "fn": total_gold_drugs - total_lookup_tp,
            "total_gold": total_gold_drugs,
        },
    ]

    # Write files
    with open(output_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with open(output_dir / "per_image.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_image_records[0].keys()))
        writer.writeheader()
        writer.writerows(per_image_records)

    with open(output_dir / "ocr_coverage.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ocr_coverage_records[0].keys()))
        writer.writeheader()
        writer.writerows(ocr_coverage_records)

    with open(output_dir / "failure_taxonomy.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["failure_stage", "count", "percentage"])
        writer.writeheader()
        for k in ["OCR_MISS", "NER_MISS", "LOOKUP_MISS", "SUCCESS"]:
            cnt = taxonomy_counts[k]
            pct = (cnt / total_gold_drugs * 100) if total_gold_drugs > 0 else 0.0
            writer.writerow({"failure_stage": k, "count": cnt, "percentage": f"{pct:.2f}%"})

    with open(output_dir / "ner_predictions.jsonl", "w", encoding="utf-8") as f:
        for r in ner_predictions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(output_dir / "lookup_predictions.jsonl", "w", encoding="utf-8") as f:
        for r in lookup_predictions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(output_dir / "error_examples.json", "w", encoding="utf-8") as f:
        json.dump(error_examples, f, ensure_ascii=False, indent=2)

    # Terminal Output
    print("\n" + "=" * 80)
    print("      VAIPE IN-DOMAIN END-TO-END DIAGNOSTIC EVALUATION RESULTS")
    print("=" * 80)
    print(f"{'Stage':<35} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 80)
    for s in summary_rows:
        print(f"{s['stage']:<35} | {s['precision']:<10} | {s['recall']:<10} | {s['f1']:<10}")
    print("=" * 80)

    print("\n--- Failure Cascade Taxonomy ---")
    for k in ["OCR_MISS", "NER_MISS", "LOOKUP_MISS", "SUCCESS"]:
        cnt = taxonomy_counts[k]
        pct = (cnt / total_gold_drugs * 100) if total_gold_drugs > 0 else 0.0
        print(f"  - {k:<15}: {cnt:4d} / {total_gold_drugs} ({pct:5.2f}%)")

    logger.info(f"VAIPE evaluation completed! Reports saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VAIPE End-to-End Diagnostic Evaluation")
    parser.add_argument("--ocr-dir", type=str, default="reports/vaipe_mlkit_end2end/mlkit_ocr", help="Directory of ML Kit OCR JSONs from Android")
    parser.add_argument("--gt-dir", type=str, default="/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/label", help="VAIPE GT label directory")
    parser.add_argument("--output-dir", type=str, default="reports/vaipe_mlkit_end2end", help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images")
    args = parser.parse_args()

    run_vaipe_benchmark(
        ocr_dir=Path(args.ocr_dir),
        gt_dir=Path(args.gt_dir),
        output_dir=Path(args.output_dir),
        limit=args.limit,
    )

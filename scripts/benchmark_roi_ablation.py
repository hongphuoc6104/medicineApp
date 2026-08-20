"""
scripts/benchmark_roi_ablation.py — 3-Tier Framing & Medication ROI Re-OCR Ablation Benchmark (C0 vs C1 vs C2).

Evaluates the real impact of image framing and medication ROI re-OCR on actual Android ML Kit Text Recognition:
- C0: Full Raw Image
- C1: Document Scanner Page Crop
- C2: Medication Table ROI Crop + Pass-2 Re-OCR on Cropped Bitmap

Uses:
- Production PhoBERT NER model (models/phobert_ner_model)
- Production DrugLookup (data/drug_db_vn_full.json)
- Real ML Kit OCR outputs from Android phone hardware (reports/medication_roi_ablation/mlkit_ocr/)
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
logger = logging.getLogger("RoiAblation")


def normalize_text(text: Optional[str]) -> str:
    """Normalize Unicode (NFC), lowercase, remove punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def extract_gold_drugs(label_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract gold drugname entities from VAIPE label JSON."""
    gold_drugs = []
    for item in label_data:
        if item.get("label") == "drugname":
            raw_text = item.get("text", "").strip()
            clean_text = re.sub(r"^(\d+[\.\/\),-:]|[①-⑩]|STT\s*[:.]?\s*\d+)\s*", "", raw_text, flags=re.IGNORECASE).strip()
            norm_text = normalize_text(clean_text)
            if norm_text:
                gold_drugs.append({
                    "id": item.get("id"),
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "normalized": norm_text,
                    "box": item.get("box"),
                })
    return gold_drugs


def check_drug_match(
    candidate_name: str,
    matched_drug_name: Optional[str],
    gold_drug: dict[str, Any],
) -> bool:
    """Check if candidate drug matches gold drug via strict or token overlap."""
    norm_cand = normalize_text(candidate_name)
    norm_matched = normalize_text(matched_drug_name)
    norm_gold = gold_drug["normalized"]

    if norm_cand == norm_gold or norm_matched == norm_gold:
        return True

    gold_tokens = [t for t in norm_gold.split() if len(t) >= 3]
    if gold_tokens:
        primary_token = gold_tokens[0]
        if primary_token in norm_cand.split() or primary_token in norm_matched.split():
            return True

    if len(norm_gold) >= 4 and (norm_gold in norm_cand or norm_cand in norm_gold):
        return True

    return False


def run_roi_ablation_eval(
    ocr_dir: Path,
    gt_dir: Path,
    output_dir: Path,
):
    """Run full C0 / C1 / C2 ablation evaluation."""
    output_dir.mkdir(parents=True, exist_ok=True)

    tiers = ["c0", "c1", "c2"]
    tier_labels = {
        "c0": "C0: Full Raw Image",
        "c1": "C1: Document Scanner Page Crop",
        "c2": "C2: Medication ROI + Re-OCR",
    }

    pipe = MedicinePipeline()

    tier_stats = {t: {"tp": 0, "fp": 0, "fn": 0, "gold_total": 0, "ocr_hits": 0, "confirmed": 0} for t in tiers}
    tier_taxonomy = {t: defaultdict(int) for t in tiers}
    per_image_records = []
    jsonl_writers = {t: open(output_dir / f"{t}_predictions.jsonl", "w", encoding="utf-8") for t in tiers}
    roi_gain_examples = []

    # Group OCR files by image_id
    ocr_files = sorted(list(ocr_dir.glob("*.json")))
    image_tier_files = defaultdict(dict)
    for f in ocr_files:
        name = f.stem
        for t in tiers:
            if name.startswith(f"{t}_"):
                img_id = name[len(t) + 1 :]
                image_tier_files[img_id][t] = f

    logger.info(f"Evaluating {len(image_tier_files)} images across 3 tiers (C0, C1, C2)...")

    for img_id, t_dict in sorted(image_tier_files.items()):
        gt_file = gt_dir / f"{img_id}.json"
        if not gt_file.exists():
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        gold_drugs = extract_gold_drugs(gt_data)
        num_gold = len(gold_drugs)
        if num_gold == 0:
            continue

        img_row = {"image_id": img_id, "gold_count": num_gold}
        tier_extractions = {}

        for tier in tiers:
            ocr_path = t_dict.get(tier)
            if not ocr_path or not ocr_path.exists():
                logger.warning(f"Missing {tier} for {img_id}")
                continue

            with open(ocr_path, "r", encoding="utf-8") as f:
                ocr_payload = json.load(f)

            raw_text = ocr_payload.get("text", "")
            norm_raw = normalize_text(raw_text)
            lines = ocr_payload.get("lines", [])

            # 1. OCR Coverage
            ocr_hits = 0
            gold_ocr_map = {}
            for g in gold_drugs:
                norm_g = g["normalized"]
                g_tokens = [tok for tok in norm_g.split() if len(tok) >= 3]
                prim = g_tokens[0] if g_tokens else norm_g
                found = norm_g in norm_raw or prim in norm_raw
                gold_ocr_map[g["id"]] = found
                if found:
                    ocr_hits += 1

            tier_stats[tier]["ocr_hits"] += ocr_hits
            tier_stats[tier]["gold_total"] += num_gold

            # 2. Pipeline Execution (P0 layout)
            res = pipe.scan_prescription_app(
                ocr_lines=lines,
                ocr_text=raw_text,
                layout_strategy="p0_raw_text",
            )
            extracted_meds = res.get("medications", [])
            tier_extractions[tier] = extracted_meds

            # 3. Match against gold drugs
            matched_gold_ids = set()
            tp = 0
            fp = 0
            confirmed = 0

            for m in extracted_meds:
                cand_name = m.get("drug_name", "") or m.get("ocr_text", "")
                matched_name = m.get("matched_drug_name")
                status = m.get("mapping_status")

                matched_g = None
                for g in gold_drugs:
                    if check_drug_match(cand_name, matched_name, g):
                        matched_g = g
                        break

                if matched_g:
                    gid = matched_g["id"]
                    if gid not in matched_gold_ids:
                        matched_gold_ids.add(gid)
                        tp += 1
                        if status == "confirmed":
                            confirmed += 1
                else:
                    fp += 1

            fn = max(0, num_gold - len(matched_gold_ids))
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / num_gold if num_gold > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            cov = ocr_hits / num_gold if num_gold > 0 else 0.0

            tier_stats[tier]["tp"] += tp
            tier_stats[tier]["fp"] += fp
            tier_stats[tier]["fn"] += fn
            tier_stats[tier]["confirmed"] += confirmed

            # Failure taxonomy
            for g in gold_drugs:
                gid = g["id"]
                if gid in matched_gold_ids:
                    tier_taxonomy[tier]["SUCCESS"] += 1
                elif not gold_ocr_map.get(gid, False):
                    tier_taxonomy[tier]["OCR_MISS"] += 1
                else:
                    tier_taxonomy[tier]["NER_MISS"] += 1

            img_row[f"{tier}_ocr_cov"] = round(cov, 4)
            img_row[f"{tier}_tp"] = tp
            img_row[f"{tier}_fp"] = fp
            img_row[f"{tier}_prec"] = round(prec, 4)
            img_row[f"{tier}_rec"] = round(rec, 4)
            img_row[f"{tier}_f1"] = round(f1, 4)

            # JSONL record
            jsonl_writers[tier].write(
                json.dumps(
                    {
                        "image_id": img_id,
                        "tier": tier,
                        "ocr_coverage": cov,
                        "tp": tp,
                        "fp": fp,
                        "fn": fn,
                        "precision": prec,
                        "recall": rec,
                        "f1": f1,
                        "extracted_medications": extracted_meds,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        # Detect ROI Gains: C2 > C0 or C2 > C1
        c0_tp = img_row.get("c0_tp", 0)
        c2_tp = img_row.get("c2_tp", 0)
        if c2_tp > c0_tp:
            roi_gain_examples.append({
                "image_id": img_id,
                "c0_extracted": [m.get("drug_name") for m in tier_extractions.get("c0", [])],
                "c1_extracted": [m.get("drug_name") for m in tier_extractions.get("c1", [])],
                "c2_extracted": [m.get("drug_name") for m in tier_extractions.get("c2", [])],
                "gold_drugs": [g.get("clean_text") for g in gold_drugs],
                "gain_notes": f"C2 recovered {c2_tp - c0_tp} additional drug(s) via tight ROI Re-OCR.",
            })

        per_image_records.append(img_row)

    for w in jsonl_writers.values():
        w.close()

    # ── 1. Summary CSV ──────────────────────────────────────────────────────
    summary_rows = []
    for tier in tiers:
        tp = tier_stats[tier]["tp"]
        fp = tier_stats[tier]["fp"]
        fn = tier_stats[tier]["fn"]
        tot_gold = tier_stats[tier]["gold_total"]
        hits = tier_stats[tier]["ocr_hits"]
        confirmed = tier_stats[tier]["confirmed"]

        cov = hits / tot_gold if tot_gold > 0 else 0.0
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / tot_gold if tot_gold > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        conf_r = confirmed / tot_gold if tot_gold > 0 else 0.0

        summary_rows.append({
            "tier": tier,
            "description": tier_labels[tier],
            "ocr_drug_coverage": round(cov, 4),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "confirmed_recall": round(conf_r, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "total_gold": tot_gold,
        })

    with open(output_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # ── 2. Per Image CSV ────────────────────────────────────────────────────
    with open(output_dir / "per_image.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_image_records[0].keys()))
        writer.writeheader()
        writer.writerows(per_image_records)

    # ── 3. Failure Taxonomy CSV ─────────────────────────────────────────────
    tax_rows = []
    for tier in tiers:
        tot_gold = tier_stats[tier]["gold_total"]
        ocr_miss = tier_taxonomy[tier]["OCR_MISS"]
        ner_miss = tier_taxonomy[tier]["NER_MISS"]
        success = tier_taxonomy[tier]["SUCCESS"]
        tax_rows.append({
            "tier": tier,
            "description": tier_labels[tier],
            "OCR_MISS": ocr_miss,
            "NER_MISS": ner_miss,
            "SUCCESS": success,
            "total_gold": tot_gold,
        })

    with open(output_dir / "failure_taxonomy.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tax_rows[0].keys()))
        writer.writeheader()
        writer.writerows(tax_rows)

    # ── 4. ROI Gain Examples JSON ───────────────────────────────────────────
    with open(output_dir / "roi_gain_examples.json", "w", encoding="utf-8") as f:
        json.dump(roi_gain_examples, f, ensure_ascii=False, indent=2)

    # ── 5. Terminal Display ─────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("     3-TIER FRAMING & MEDICATION ROI RE-OCR ABLATION BENCHMARK (C0 vs C1 vs C2)")
    print("=" * 96)
    print(f"{'Experiment Tier':<35} | {'OCR Coverage':<13} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 96)
    for s in summary_rows:
        print(f"{s['description']:<35} | {s['ocr_drug_coverage']*100:<12.2f}% | {s['precision']*100:<9.2f}% | {s['recall']*100:<9.2f}% | {s['f1_score']*100:<9.2f}%")
    print("=" * 96)

    print("\n--- Failure Taxonomy Breakdown ---")
    print(f"{'Tier':<10} | {'OCR_MISS':<12} | {'NER_MISS':<12} | {'SUCCESS':<12} | {'Total Gold':<12}")
    print("-" * 65)
    for t in tax_rows:
        print(f"{t['tier']:<10} | {t['OCR_MISS']:<12} | {t['NER_MISS']:<12} | {t['SUCCESS']:<12} | {t['total_gold']:<12}")
    print("-" * 65)

    print(f"\nDiscovered {len(roi_gain_examples)} concrete examples where C2 Medication ROI recovered missed drugs!")
    logger.info(f"ROI Ablation completed! All reports saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3-Tier ROI Ablation Benchmark")
    parser.add_argument("--ocr-dir", type=str, default="reports/medication_roi_ablation/mlkit_ocr", help="Directory of ML Kit OCR JSONs")
    parser.add_argument("--gt-dir", type=str, default="/home/hongphuoc/Desktop/KHMT-2025-2026/NienLuanNganh/vaipe-p/public_train/label", help="VAIPE GT label directory")
    parser.add_argument("--output-dir", type=str, default="reports/medication_roi_ablation", help="Output directory")
    args = parser.parse_args()

    run_roi_ablation_eval(
        ocr_dir=Path(args.ocr_dir),
        gt_dir=Path(args.gt_dir),
        output_dir=Path(args.output_dir),
    )

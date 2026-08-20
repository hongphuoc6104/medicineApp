"""
scripts/benchmark_real_medication_roi.py — Real-World Hard Camera Capture Medication ROI Re-OCR Benchmark (R0 vs R1).

Evaluates the real impact of user-guided medication table ROI cropping and pass-2 re-OCR
on hard real-world camera captures (where full-page OCR suffered low recall):
- R0: Full-Page Smartphone Camera Capture
- R1: Medication Table ROI Crop + Pass-2 Re-OCR on Cropped Bitmap

Uses:
- Production PhoBERT NER model (models/phobert_ner_model)
- Production DrugLookup (data/drug_db_vn_full.json)
- Real ML Kit OCR outputs from Android phone hardware (reports/real_medication_roi_ablation/mlkit_ocr/)
- Canonical Ground Truth (../medicineApp-rxie/data/canonical_ground_truth/)
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
logger = logging.getLogger("RealRoiAblation")


def normalize_text(text: Optional[str]) -> str:
    """Normalize Unicode (NFC), lowercase, remove punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def match_drug(
    candidate_name: str,
    matched_drug_name: Optional[str],
    gt_med: dict[str, Any],
) -> bool:
    """Check if candidate drug matches canonical ground truth."""
    norm_cand = normalize_text(candidate_name)
    norm_matched = normalize_text(matched_drug_name)

    targets = [
        normalize_text(gt_med.get("brand_normalized")),
        normalize_text(gt_med.get("drug_normalized")),
        normalize_text(gt_med.get("brand_raw")),
        normalize_text(gt_med.get("drug_raw")),
    ]
    targets = [t for t in targets if t and len(t) >= 3]

    for t in targets:
        if norm_cand == t or norm_matched == t:
            return True
        if len(t) >= 4 and (t in norm_cand.split() or t in norm_matched.split()):
            return True
        if len(t) >= 4 and (t in norm_cand or norm_cand in t or t in norm_matched):
            return True

    return False


def run_real_roi_evaluation(
    ocr_dir: Path,
    gt_dir: Path,
    output_dir: Path,
):
    """Evaluate R0 vs R1 on real hard captures."""
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = ["r0", "r1"]
    cond_labels = {
        "r0": "R0: Full-Page Smartphone Capture",
        "r1": "R1: Medication Table ROI Re-OCR",
    }

    pipe = MedicinePipeline()

    cond_stats = {c: {"tp": 0, "fp": 0, "fn": 0, "gold_total": 0, "ocr_hits": 0, "confirmed": 0} for c in conditions}
    cond_taxonomy = {c: defaultdict(int) for c in conditions}
    per_capture_records = []
    jsonl_writers = {c: open(output_dir / f"{c}_predictions.jsonl", "w", encoding="utf-8") for c in conditions}
    recovered_drugs = []

    # Map files by image_id
    ocr_files = sorted(list(ocr_dir.glob("*.json")))
    capture_map = defaultdict(dict)
    for f in ocr_files:
        name = f.stem
        for c in conditions:
            if name.startswith(f"{c}_"):
                img_id = name[len(c) + 1 :]
                capture_map[img_id][c] = f

    logger.info(f"Evaluating {len(capture_map)} hard real camera captures for R0 vs R1...")

    for img_id, c_dict in sorted(capture_map.items()):
        # Determine prescription ID from payload
        sample_ocr = c_dict.get("r0") or c_dict.get("r1")
        with open(sample_ocr, "r", encoding="utf-8") as f:
            meta = json.load(f)
        pid = meta.get("prescription_id", "RX_001")

        gt_file = gt_dir / f"{pid}.json"
        if not gt_file.exists():
            continue

        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        gt_meds = gt_data.get("medications", [])
        num_gold = len(gt_meds)
        if num_gold == 0:
            continue

        cap_row = {"image_id": img_id, "prescription_id": pid, "gold_count": num_gold}
        cond_extracted_meds = {}

        for cond in conditions:
            ocr_path = c_dict.get(cond)
            if not ocr_path or not ocr_path.exists():
                logger.warning(f"Missing {cond} for {img_id}")
                continue

            with open(ocr_path, "r", encoding="utf-8") as f:
                ocr_payload = json.load(f)

            raw_text = ocr_payload.get("text", "")
            norm_raw = normalize_text(raw_text)
            lines = ocr_payload.get("lines", [])

            # 1. OCR Drug Coverage
            ocr_hits = 0
            gold_ocr_map = {}
            for g in gt_meds:
                targets = [
                    normalize_text(g.get("brand_normalized")),
                    normalize_text(g.get("drug_normalized")),
                    normalize_text(g.get("brand_raw")),
                ]
                targets = [t for t in targets if t and len(t) >= 3]
                found = any(t in norm_raw for t in targets)
                gid = g.get("medication_id", id(g))
                gold_ocr_map[gid] = found
                if found:
                    ocr_hits += 1

            cond_stats[cond]["ocr_hits"] += ocr_hits
            cond_stats[cond]["gold_total"] += num_gold

            # 2. Pipeline Execution (P0 layout)
            res = pipe.scan_prescription_app(
                ocr_lines=lines,
                ocr_text=raw_text,
                layout_strategy="p0_raw_text",
            )
            extracted = res.get("medications", [])
            cond_extracted_meds[cond] = extracted

            # 3. Match against GT
            matched_gold_ids = set()
            tp = 0
            fp = 0
            confirmed = 0

            for m in extracted:
                cname = m.get("drug_name", "") or m.get("ocr_text", "")
                mname = m.get("matched_drug_name")
                status = m.get("mapping_status")

                matched_gt = None
                for g in gt_meds:
                    if match_drug(cname, mname, g):
                        matched_gt = g
                        break

                if matched_gt:
                    gid = matched_gt.get("medication_id", id(matched_gt))
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

            cond_stats[cond]["tp"] += tp
            cond_stats[cond]["fp"] += fp
            cond_stats[cond]["fn"] += fn
            cond_stats[cond]["confirmed"] += confirmed

            # Failure taxonomy
            for g in gt_meds:
                gid = g.get("medication_id", id(g))
                if gid in matched_gold_ids:
                    cond_taxonomy[cond]["SUCCESS"] += 1
                elif not gold_ocr_map.get(gid, False):
                    cond_taxonomy[cond]["OCR_MISS"] += 1
                else:
                    cond_taxonomy[cond]["NER_MISS"] += 1

            cap_row[f"{cond}_ocr_cov"] = round(cov, 4)
            cap_row[f"{cond}_tp"] = tp
            cap_row[f"{cond}_fp"] = fp
            cap_row[f"{cond}_prec"] = round(prec, 4)
            cap_row[f"{cond}_rec"] = round(rec, 4)
            cap_row[f"{cond}_f1"] = round(f1, 4)

            # JSONL prediction
            jsonl_writers[cond].write(
                json.dumps(
                    {
                        "image_id": img_id,
                        "prescription_id": pid,
                        "condition": cond,
                        "ocr_coverage": cov,
                        "tp": tp,
                        "fp": fp,
                        "fn": fn,
                        "precision": prec,
                        "recall": rec,
                        "f1": f1,
                        "extracted_medications": extracted,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        # Detect R1 Gain
        r0_tp = cap_row.get("r0_tp", 0)
        r1_tp = cap_row.get("r1_tp", 0)
        if r1_tp > r0_tp:
            recovered_drugs.append({
                "image_id": img_id,
                "prescription_id": pid,
                "r0_extracted": [m.get("drug_name") for m in cond_extracted_meds.get("r0", [])],
                "r1_extracted": [m.get("drug_name") for m in cond_extracted_meds.get("r1", [])],
                "gt_drugs": [g.get("brand_raw") or g.get("drug_raw") for g in gt_meds],
                "gain": f"R1 recovered +{r1_tp - r0_tp} drug(s) missed in full page photo.",
            })

        per_capture_records.append(cap_row)

    for w in jsonl_writers.values():
        w.close()

    # ── 1. Summary CSV ──────────────────────────────────────────────────────
    summary_rows = []
    for cond in conditions:
        tp = cond_stats[cond]["tp"]
        fp = cond_stats[cond]["fp"]
        fn = cond_stats[cond]["fn"]
        tot_gold = cond_stats[cond]["gold_total"]
        hits = cond_stats[cond]["ocr_hits"]
        confirmed = cond_stats[cond]["confirmed"]

        cov = hits / tot_gold if tot_gold > 0 else 0.0
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / tot_gold if tot_gold > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        conf_r = confirmed / tot_gold if tot_gold > 0 else 0.0

        summary_rows.append({
            "condition": cond,
            "description": cond_labels[cond],
            "ocr_drug_coverage": round(cov, 4),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "lookup_confirmed_recall": round(conf_r, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "total_gold": tot_gold,
        })

    with open(output_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # ── 2. Per Capture CSV ──────────────────────────────────────────────────
    with open(output_dir / "per_capture.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_capture_records[0].keys()))
        writer.writeheader()
        writer.writerows(per_capture_records)

    # ── 3. Failure Taxonomy CSV ─────────────────────────────────────────────
    tax_rows = []
    for cond in conditions:
        tot_gold = cond_stats[cond]["gold_total"]
        ocr_miss = cond_taxonomy[cond]["OCR_MISS"]
        ner_miss = cond_taxonomy[cond]["NER_MISS"]
        success = cond_taxonomy[cond]["SUCCESS"]
        tax_rows.append({
            "condition": cond,
            "description": cond_labels[cond],
            "OCR_MISS": ocr_miss,
            "NER_MISS": ner_miss,
            "SUCCESS": success,
            "total_gold": tot_gold,
        })

    with open(output_dir / "failure_taxonomy.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tax_rows[0].keys()))
        writer.writeheader()
        writer.writerows(tax_rows)

    # ── 4. Recovered Drugs JSON ─────────────────────────────────────────────
    with open(output_dir / "r1_recovered_drugs.json", "w", encoding="utf-8") as f:
        json.dump(recovered_drugs, f, ensure_ascii=False, indent=2)

    # ── 5. Terminal Display ─────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("      REAL-WORLD CAMERA CAPTURE MEDICATION ROI RE-OCR BENCHMARK (R0 vs R1)")
    print("=" * 96)
    print(f"{'Condition':<35} | {'OCR Coverage':<13} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 96)
    for s in summary_rows:
        print(f"{s['description']:<35} | {s['ocr_drug_coverage']*100:<12.2f}% | {s['precision']*100:<9.2f}% | {s['recall']*100:<9.2f}% | {s['f1_score']*100:<9.2f}%")
    print("=" * 96)

    # Compute Delta
    r0_cov = summary_rows[0]["ocr_drug_coverage"] * 100
    r1_cov = summary_rows[1]["ocr_drug_coverage"] * 100
    r0_rec = summary_rows[0]["recall"] * 100
    r1_rec = summary_rows[1]["recall"] * 100
    r0_f1 = summary_rows[0]["f1_score"] * 100
    r1_f1 = summary_rows[1]["f1_score"] * 100

    print(f"\n★ DELTA GAIN (R1 vs R0):")
    print(f"  - OCR Drug Coverage : {r0_cov:5.2f}% ──▶ {r1_cov:5.2f}%  (+{r1_cov - r0_cov:5.2f}%)")
    print(f"  - End-to-End Recall : {r0_rec:5.2f}% ──▶ {r1_rec:5.2f}%  (+{r1_rec - r0_rec:5.2f}%)")
    print(f"  - End-to-End F1     : {r0_f1:5.2f}% ──▶ {r1_f1:5.2f}%  (+{r1_f1 - r0_f1:5.2f}%)")

    print("\n--- Failure Taxonomy Breakdown ---")
    print(f"{'Condition':<10} | {'OCR_MISS':<12} | {'NER_MISS':<12} | {'SUCCESS':<12} | {'Total Gold':<12}")
    print("-" * 65)
    for t in tax_rows:
        print(f"{t['condition']:<10} | {t['OCR_MISS']:<12} | {t['NER_MISS']:<12} | {t['SUCCESS']:<12} | {t['total_gold']:<12}")
    print("-" * 65)

    print(f"\nDiscovered {len(recovered_drugs)} concrete hard camera captures where R1 Medication Table Re-OCR recovered missed drugs!")
    logger.info(f"Real ROI Benchmark completed! All reports saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real Camera Medication ROI Ablation Benchmark")
    parser.add_argument("--ocr-dir", type=str, default="reports/real_medication_roi_ablation/mlkit_ocr", help="Directory of ML Kit OCR JSONs")
    parser.add_argument("--gt-dir", type=str, default="../medicineApp-rxie/data/canonical_ground_truth", help="Canonical GT directory")
    parser.add_argument("--output-dir", type=str, default="reports/real_medication_roi_ablation", help="Output directory")
    args = parser.parse_args()

    run_real_roi_evaluation(
        ocr_dir=Path(args.ocr_dir),
        gt_dir=Path(args.gt_dir),
        output_dir=Path(args.output_dir),
    )

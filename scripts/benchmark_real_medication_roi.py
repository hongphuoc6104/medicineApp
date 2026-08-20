"""
scripts/benchmark_real_medication_roi.py — Real-World Hard Camera Capture Medication ROI Re-OCR Benchmark (R0 vs R1).

Evaluates R0 (Full-Page Smartphone Camera Capture) vs R1 (Medication Table ROI Crop + Pass-2 Re-OCR)
against Visible-in-frame Ground Truth on 30 hard real camera captures.

Uses:
- Production PhoBERT NER model (models/phobert_ner_model)
- Production DrugLookup (data/drug_db_vn_full.json)
- Real ML Kit OCR outputs from Android phone hardware (reports/real_medication_roi_ablation/mlkit_ocr/)
- Visible-in-Frame Ground Truth (data/visible_in_frame_gt.json)
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


def check_drug_match_visible(
    candidate_name: str,
    matched_drug_name: Optional[str],
    gold_drug_str: str,
) -> bool:
    """Check if candidate drug matches visible gold drug."""
    norm_cand = normalize_text(candidate_name)
    norm_matched = normalize_text(matched_drug_name)
    norm_gold = normalize_text(gold_drug_str)

    if norm_cand == norm_gold or norm_matched == norm_gold:
        return True

    gold_tokens = [t for t in norm_gold.split() if len(t) >= 3]
    if gold_tokens:
        primary_tok = gold_tokens[0]
        if primary_tok in norm_cand.split() or primary_tok in norm_matched.split():
            return True

    if len(norm_gold) >= 4 and (norm_gold in norm_cand or norm_cand in norm_gold or norm_gold in norm_matched):
        return True

    return False


def run_real_roi_evaluation(
    ocr_dir: Path,
    visible_gt_path: Path,
    output_dir: Path,
):
    """Evaluate R0 vs R1 against Visible-in-frame Ground Truth."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(visible_gt_path, "r", encoding="utf-8") as f:
        visible_gt_map = json.load(f)

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

    # Paired transitions tracking
    # Key: (image_id, gold_drug) -> {"r0_correct": bool, "r1_correct": bool}
    paired_item_results = defaultdict(lambda: {"r0_correct": False, "r1_correct": False})

    # Group OCR files by image_id
    ocr_files = sorted(list(ocr_dir.glob("*.json")))
    capture_map = defaultdict(dict)
    for f in ocr_files:
        name = f.stem
        for c in conditions:
            if name.startswith(f"{c}_"):
                img_id = name[len(c) + 1 :]
                capture_map[img_id][c] = f

    logger.info(f"Evaluating {len(capture_map)} hard real captures with Visible-in-Frame Ground Truth...")

    for img_id, c_dict in sorted(capture_map.items()):
        if img_id not in visible_gt_map:
            logger.warning(f"No visible GT for {img_id}, skipping.")
            continue

        gt_info = visible_gt_map[img_id]
        pid = gt_info["prescription_id"]
        visible_drugs = gt_info["visible_drugs"]
        num_gold = len(visible_drugs)

        cap_row = {"image_id": img_id, "prescription_id": pid, "visible_gold_count": num_gold}
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

            # 1. OCR Drug Coverage on Visible Drugs
            ocr_hits = 0
            gold_ocr_map = {}
            for g_drug in visible_drugs:
                norm_g = normalize_text(g_drug)
                g_tokens = [tok for tok in norm_g.split() if len(tok) >= 3]
                prim = g_tokens[0] if g_tokens else norm_g
                found = norm_g in norm_raw or prim in norm_raw
                gold_ocr_map[g_drug] = found
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

            # 3. Match against visible drugs
            matched_gold_set = set()
            tp = 0
            fp = 0
            confirmed = 0

            for m in extracted:
                cname = m.get("drug_name", "") or m.get("ocr_text", "")
                mname = m.get("matched_drug_name")
                status = m.get("mapping_status")

                matched_g = None
                for g_drug in visible_drugs:
                    if check_drug_match_visible(cname, mname, g_drug):
                        matched_g = g_drug
                        break

                if matched_g:
                    if matched_g not in matched_gold_set:
                        matched_gold_set.add(matched_g)
                        tp += 1
                        if status == "confirmed":
                            confirmed += 1
                else:
                    fp += 1

            fn = max(0, num_gold - len(matched_gold_set))
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / num_gold if num_gold > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            cov = ocr_hits / num_gold if num_gold > 0 else 0.0

            cond_stats[cond]["tp"] += tp
            cond_stats[cond]["fp"] += fp
            cond_stats[cond]["fn"] += fn
            cond_stats[cond]["confirmed"] += confirmed

            # Record paired item transitions
            for g_drug in visible_drugs:
                is_correct = g_drug in matched_gold_set
                paired_item_results[(img_id, g_drug)][f"{cond}_correct"] = is_correct

                if is_correct:
                    cond_taxonomy[cond]["SUCCESS"] += 1
                elif not gold_ocr_map.get(g_drug, False):
                    cond_taxonomy[cond]["OCR_MISS"] += 1
                else:
                    cond_taxonomy[cond]["NER_MISS"] += 1

            cap_row[f"{cond}_ocr_cov"] = round(cov, 4)
            cap_row[f"{cond}_tp"] = tp
            cap_row[f"{cond}_fp"] = fp
            cap_row[f"{cond}_prec"] = round(prec, 4)
            cap_row[f"{cond}_rec"] = round(rec, 4)
            cap_row[f"{cond}_f1"] = round(f1, 4)

            # Write JSONL prediction
            jsonl_writers[cond].write(
                json.dumps(
                    {
                        "image_id": img_id,
                        "prescription_id": pid,
                        "condition": cond,
                        "visible_ocr_coverage": cov,
                        "tp": tp,
                        "fp": fp,
                        "fn": fn,
                        "precision": prec,
                        "recall": rec,
                        "f1": f1,
                        "extracted_medications": extracted,
                        "visible_drugs": visible_drugs,
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
                "visible_drugs": visible_drugs,
                "gain": f"R1 recovered +{r1_tp - r0_tp} drug(s) missed in full page photo.",
            })

        per_capture_records.append(cap_row)

    for w in jsonl_writers.values():
        w.close()

    # ── 1. Summary CSV (Visible Metrics) ────────────────────────────────────
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
            "visible_ocr_coverage": round(cov, 4),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "lookup_confirmed_recall": round(conf_r, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "total_visible_gold": tot_gold,
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
            "total_visible_gold": tot_gold,
        })

    with open(output_dir / "failure_taxonomy.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tax_rows[0].keys()))
        writer.writeheader()
        writer.writerows(tax_rows)

    # ── 4. Paired Transition Matrix CSV ─────────────────────────────────────
    trans_counts = {
        "r0_correct_r1_correct": 0,
        "r0_wrong_r1_correct": 0, # Gain
        "r0_correct_r1_wrong": 0, # Loss
        "r0_wrong_r1_wrong": 0,
    }
    for (img_id, drug), p_res in paired_item_results.items():
        r0_c = p_res["r0_correct"]
        r1_c = p_res["r1_correct"]
        if r0_c and r1_c:
            trans_counts["r0_correct_r1_correct"] += 1
        elif (not r0_c) and r1_c:
            trans_counts["r0_wrong_r1_correct"] += 1
        elif r0_c and (not r1_c):
            trans_counts["r0_correct_r1_wrong"] += 1
        else:
            trans_counts["r0_wrong_r1_wrong"] += 1

    trans_rows = [
        {"transition": "R0 Correct ──▶ R1 Correct (Both Success)", "count": trans_counts["r0_correct_r1_correct"]},
        {"transition": "R0 Wrong   ──▶ R1 Correct (R1 Recovery Gain ★)", "count": trans_counts["r0_wrong_r1_correct"]},
        {"transition": "R0 Correct ──▶ R1 Wrong   (R1 Regression Loss)", "count": trans_counts["r0_correct_r1_wrong"]},
        {"transition": "R0 Wrong   ──▶ R1 Wrong   (Both Missed)", "count": trans_counts["r0_wrong_r1_wrong"]},
        {"transition": "TOTAL VISIBLE DRUG INSTANCES", "count": len(paired_item_results)},
    ]

    with open(output_dir / "paired_transition_matrix.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["transition", "count"])
        writer.writeheader()
        writer.writerows(trans_rows)

    # ── 5. Recovered Drugs JSON ─────────────────────────────────────────────
    with open(output_dir / "r1_recovered_drugs.json", "w", encoding="utf-8") as f:
        json.dump(recovered_drugs, f, ensure_ascii=False, indent=2)

    # ── 6. Terminal Display ─────────────────────────────────────────────────
    print("\n" + "=" * 98)
    print("   REAL-WORLD HARD CAMERA CAPTURES: R0 vs R1 EVALUATION (VISIBLE-IN-FRAME GROUND TRUTH)")
    print("=" * 98)
    print(f"{'Condition':<35} | {'Visible OCR Cov':<16} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 98)
    for s in summary_rows:
        print(f"{s['description']:<35} | {s['visible_ocr_coverage']*100:<15.2f}% | {s['precision']*100:<9.2f}% | {s['recall']*100:<9.2f}% | {s['f1_score']*100:<9.2f}%")
    print("=" * 98)

    print("\n--- Paired Drug-Level Transition Matrix ---")
    for t in trans_rows:
        print(f"  * {t['transition']:<52}: {t['count']:3d}")

    net_gain = trans_counts["r0_wrong_r1_correct"] - trans_counts["r0_correct_r1_wrong"]
    print(f"  * NET RECOVERY GAIN (R1 Gain - R1 Loss): {'+' if net_gain >= 0 else ''}{net_gain} drugs")

    print("\n--- Failure Taxonomy on Physically Visible Drugs ---")
    print(f"{'Condition':<10} | {'OCR_MISS':<12} | {'NER_MISS':<12} | {'SUCCESS':<12} | {'Total Visible':<14}")
    print("-" * 68)
    for t in tax_rows:
        print(f"{t['condition']:<10} | {t['OCR_MISS']:<12} | {t['NER_MISS']:<12} | {t['SUCCESS']:<12} | {t['total_visible_gold']:<14}")
    print("-" * 68)

    print(f"\nDiscovered {len(recovered_drugs)} hard camera captures with qualitative drug recoveries.")
    logger.info(f"Visible Evaluation completed! All reports saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visible-in-frame Real Camera ROI Benchmark")
    parser.add_argument("--ocr-dir", type=str, default="reports/real_medication_roi_ablation/mlkit_ocr", help="Directory of ML Kit OCR JSONs")
    parser.add_argument("--visible-gt", type=str, default="data/visible_in_frame_gt.json", help="Visible GT JSON file")
    parser.add_argument("--output-dir", type=str, default="reports/real_medication_roi_ablation", help="Output directory")
    args = parser.parse_args()

    run_real_roi_evaluation(
        ocr_dir=Path(args.ocr_dir),
        visible_gt_path=Path(args.visible_gt),
        output_dir=Path(args.output_dir),
    )

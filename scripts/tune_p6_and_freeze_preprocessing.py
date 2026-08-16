#!/usr/bin/env python3
"""
RxIE Preprocessing Ablation & P6 Selector Tuning using Field-Level Medication CER/Accuracy on 140 Tuning Images,
followed by single-pass confirmation on 60 Held-out Test Images.
"""

import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath("src"))

from rxie.preprocessing_eval import (
    calculate_item_cer,
    compare_paired_ocr_items,
)


def load_branch_ocr_outputs(branch_dir: str) -> dict[str, dict]:
    json_files = glob.glob(f"{branch_dir}/**/*.json", recursive=True)
    outputs = {}
    for p in json_files:
        bid = os.path.splitext(os.path.basename(p))[0]
        if "mlkit_ocr" in p and bid in outputs:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            blocks = d.get("blocks", [])
            lines = [l.get("text", "").strip() for b in blocks for l in b.get("lines", []) if l.get("text", "").strip()]
            full_text = " ".join(lines)
            outputs[bid] = {
                "file": p,
                "lines": lines,
                "text": full_text,
                "word_count": len(full_text.split()),
                "line_count": len(lines),
            }
        except Exception:
            pass
    return outputs


def evaluate_branch_records(
    selected_outputs: dict[str, dict],
    benchmark_records: dict[str, dict],
    split_role: str = "tuning",
) -> dict:
    cers = []
    drug_accs = []
    strength_accs = []
    qty_accs = []

    for image_id, rec in benchmark_records.items():
        if rec.get("split_role") != split_role:
            continue
        if image_id not in selected_outputs:
            continue

        ocr_info = selected_outputs[image_id]
        lines = ocr_info["lines"]
        full_lower = ocr_info["text"].lower()

        gold_meds = rec.get("medications", [])
        gold_items = []
        d_matches = 0
        s_matches = 0
        q_matches = 0

        for m in gold_meds:
            if m.get("drug_raw"):
                gold_items.append(m["drug_raw"])
            if m.get("instruction_raw"):
                gold_items.append(m["instruction_raw"])

            # Normalized Drug / Brand matching
            d_norm = m.get("drug_normalized", "").lower()
            b_norm = m.get("brand_normalized", "").lower()
            if (d_norm and d_norm in full_lower) or (b_norm and b_norm in full_lower) or (m.get("drug_raw", "").lower() in full_lower):
                d_matches += 1

            s_raw = (m.get("strength_raw") or "").lower()
            if s_raw and s_raw in full_lower:
                s_matches += 1

            q_val = str(m.get("quantity_value_raw") or "")
            if q_val and q_val in ocr_info["text"]:
                q_matches += 1

        img_cer = statistics.mean([calculate_item_cer(it, lines) for it in gold_items]) if gold_items else 0.0
        cers.append(img_cer)

        n_meds = len(gold_meds) if gold_meds else 1
        drug_accs.append(d_matches / n_meds)
        strength_accs.append(s_matches / n_meds)
        qty_accs.append(q_matches / n_meds)

    return {
        "count": len(cers),
        "mean_cer": statistics.mean(cers) if cers else 0.0,
        "median_cer": statistics.median(cers) if cers else 0.0,
        "drug_accuracy": statistics.mean(drug_accs) if drug_accs else 0.0,
        "strength_accuracy": statistics.mean(strength_accs) if strength_accs else 0.0,
        "quantity_accuracy": statistics.mean(qty_accs) if qty_accs else 0.0,
    }


def compute_paired_degradation(
    base_outputs: dict[str, dict],
    eval_outputs: dict[str, dict],
    benchmark_records: dict[str, dict],
    split_role: str = "tuning",
) -> dict:
    improved = 0
    degraded = 0
    equal = 0
    total = 0

    for image_id, rec in benchmark_records.items():
        if rec.get("split_role") != split_role:
            continue
        if image_id not in base_outputs or image_id not in eval_outputs:
            continue

        gold_meds = rec.get("medications", [])
        gold_items = [m["drug_raw"] for m in gold_meds if m.get("drug_raw")] + [m["instruction_raw"] for m in gold_meds if m.get("instruction_raw")]

        lines_base = base_outputs[image_id]["lines"]
        lines_eval = eval_outputs[image_id]["lines"]

        comp = compare_paired_ocr_items(gold_items, lines_base, lines_eval)
        total += 1
        if comp.is_improved:
            improved += 1
        elif comp.is_degraded:
            degraded += 1
        else:
            equal += 1

    return {
        "total": total,
        "improved_count": improved,
        "improved_rate": improved / total if total else 0.0,
        "degraded_count": degraded,
        "degraded_rate": degraded / total if total else 0.0,
        "equal_count": equal,
    }


def main():
    benchmark_gt_path = "data/manifests/benchmark_200_gt.json"
    tracking_meta_path = "data/ablation_metadata_tracking.json"

    with open(benchmark_gt_path, "r", encoding="utf-8") as f:
        benchmark_gt = json.load(f)
    records = benchmark_gt["records"]

    tracking_meta = {}
    if os.path.exists(tracking_meta_path):
        with open(tracking_meta_path, "r", encoding="utf-8") as f:
            tracking_meta = json.load(f)

    # Load all branch outputs
    branches = {
        "P0 RAW": load_branch_ocr_outputs("data/output"),
        "P1 Rotation": load_branch_ocr_outputs("data/output_p1"),
        "P2 Perspective": load_branch_ocr_outputs("data/output_p2"),
        "P3 Deskew": load_branch_ocr_outputs("data/output_p3"),
        "P4 Rectified": load_branch_ocr_outputs("data/output_rectified"),
    }

    print("=========================================================================================")
    print("        RxIE PREPROCESSING ABLATION STUDY & P6 TUNING (140 TUNING IMAGES)                ")
    print("=========================================================================================")

    p0_out = branches["P0 RAW"]

    tuning_results = {}
    degradations = {}

    for name, b_out in branches.items():
        res = evaluate_branch_records(b_out, records, split_role="tuning")
        deg = compute_paired_degradation(p0_out, b_out, records, split_role="tuning")
        tuning_results[name] = res
        degradations[name] = deg

    # Print 140 Tuning Evaluation Table
    header = f"{'Branch':<16} | {'Med CER':<9} | {'Drug Acc':<10} | {'Str Acc':<9} | {'Qty Acc':<9} | {'Improved':<9} | {'Degraded'}"
    print(header)
    print("-" * 80)

    for name in branches:
        r = tuning_results[name]
        d = degradations[name]
        print(
            f"{name:<16} | "
            f"{r['mean_cer']*100:>7.2f}% | "
            f"{r['drug_accuracy']*100:>8.2f}% | "
            f"{r['strength_accuracy']*100:>7.2f}% | "
            f"{r['quantity_accuracy']*100:>7.2f}% | "
            f"{d['improved_count']:>4} ({d['improved_rate']*100:>4.1f}%) | "
            f"{d['degraded_count']:>4} ({d['degraded_rate']*100:>4.1f}%)"
        )

    print("\n-----------------------------------------------------------------------------------------")
    print("🔍 [P6 Selector Policy Tuning on 140 Tuning Images]")
    print("-----------------------------------------------------------------------------------------")

    p6_candidates = {}

    # Policy 1: Deskew @ 4°
    p6_4deg = {}
    for iid, p0_info in p0_out.items():
        meta = tracking_meta.get(iid, {})
        deskew_ang = abs(meta.get("deskew_detected_angle", 0.0))
        if deskew_ang >= 4.0 and iid in branches["P4 Rectified"]:
            p6_4deg[iid] = branches["P4 Rectified"][iid]
        elif iid in branches["P1 Rotation"]:
            p6_4deg[iid] = branches["P1 Rotation"][iid]
        else:
            p6_4deg[iid] = p0_info
    p6_candidates["P6 (Gated Deskew >= 4°)"] = p6_4deg

    # Policy 2: Deskew @ 6°
    p6_6deg = {}
    for iid, p0_info in p0_out.items():
        meta = tracking_meta.get(iid, {})
        deskew_ang = abs(meta.get("deskew_detected_angle", 0.0))
        if deskew_ang >= 6.0 and iid in branches["P4 Rectified"]:
            p6_6deg[iid] = branches["P4 Rectified"][iid]
        elif iid in branches["P1 Rotation"]:
            p6_6deg[iid] = branches["P1 Rotation"][iid]
        else:
            p6_6deg[iid] = p0_info
    p6_candidates["P6 (Gated Deskew >= 6°)"] = p6_6deg

    # Policy 3: Hybrid Quality Guard (P1 if rotated, P4 if skewed >= 6° and no word loss, else P0)
    p6_hybrid = {}
    p6_selection_log = {}
    for iid, p0_info in p0_out.items():
        p1_info = branches["P1 Rotation"].get(iid, p0_info)
        p4_info = branches["P4 Rectified"].get(iid, p0_info)

        meta = tracking_meta.get(iid, {})
        rot = meta.get("rotation_applied", 0)
        deskew_ang = abs(meta.get("deskew_detected_angle", 0.0))

        if p4_info["word_count"] < p1_info["word_count"] * 0.85:
            choice = "P1"
            p6_hybrid[iid] = p1_info
        elif rot > 0:
            if deskew_ang >= 6.0 and p4_info["word_count"] >= p1_info["word_count"] * 0.95:
                choice = "P4"
                p6_hybrid[iid] = p4_info
            else:
                choice = "P1"
                p6_hybrid[iid] = p1_info
        elif deskew_ang >= 6.0 and p4_info["word_count"] >= p0_info["word_count"] * 0.95:
            choice = "P4"
            p6_hybrid[iid] = p4_info
        else:
            choice = "P0"
            p6_hybrid[iid] = p0_info

        p6_selection_log[iid] = choice

    p6_candidates["P6 (Hybrid Quality Guard)"] = p6_hybrid

    for name, c_out in p6_candidates.items():
        r = evaluate_branch_records(c_out, records, split_role="tuning")
        d = compute_paired_degradation(p0_out, c_out, records, split_role="tuning")
        print(
            f"{name:<28} | "
            f"Med CER: {r['mean_cer']*100:>5.2f}% | "
            f"Drug Acc: {r['drug_accuracy']*100:>5.2f}% | "
            f"Str Acc: {r['strength_accuracy']*100:>5.2f}% | "
            f"Degraded: {d['degraded_count']} ({d['degraded_rate']*100:.1f}%)"
        )

    p6_final = p6_candidates["P6 (Hybrid Quality Guard)"]

    print("\n=========================================================================================")
    print("🔒 [PREPROCESSING V1 FROZEN SPECIFICATION]")
    print("=========================================================================================")
    print("  • ROTATION (P1)    : KEEP (0/90/180/270 orientation normalization)")
    print("  • PERSPECTIVE (P2) : DROP (0/200 activations on real dataset)")
    print("  • DESKEW (P3)      : CONDITIONAL (Threshold |angle| >= 6.0° with text preservation guard)")
    print("  • SELECTOR (P6)    : Hybrid Quality Guard (P1/P4 with P0 fallback)")
    print("=========================================================================================\n")

    # Step 4: Open 60 Held-out Test Images EXACTLY ONCE
    print("=========================================================================================")
    print("🎯 [FINAL CONFIRMATION ON 60 HELD-OUT TEST IMAGES (SINGLE PASS)]                          ")
    print("=========================================================================================")

    test_branches = {
        "P0 RAW": branches["P0 RAW"],
        "P1 Rotation": branches["P1 Rotation"],
        "P4 Rectified": branches["P4 Rectified"],
        "P6 Final": p6_final,
    }

    test_results = {}
    test_degradations = {}

    header_test = f"{'Branch':<16} | {'Med CER':<9} | {'Drug Acc':<10} | {'Str Acc':<9} | {'Qty Acc':<9} | {'Degraded'}"
    print(header_test)
    print("-" * 80)

    for name, b_out in test_branches.items():
        r = evaluate_branch_records(b_out, records, split_role="test")
        d = compute_paired_degradation(p0_out, b_out, records, split_role="test")
        test_results[name] = r
        test_degradations[name] = d
        print(
            f"{name:<16} | "
            f"{r['mean_cer']*100:>7.2f}% | "
            f"{r['drug_accuracy']*100:>8.2f}% | "
            f"{r['strength_accuracy']*100:>7.2f}% | "
            f"{r['quantity_accuracy']*100:>7.2f}% | "
            f"{d['degraded_count']:>4} ({d['degraded_rate']*100:>4.1f}%)"
        )

    print("=========================================================================================\n")

    spec_export = {
        "schema_version": "rxie.preprocessing_spec.v1",
        "status": "FROZEN",
        "rules": {
            "rotation": "ALWAYS_APPLY",
            "perspective": "DROP",
            "deskew": "CONDITIONAL_GE_6_DEG",
            "selector": "P6_HYBRID_QUALITY_GUARD",
        },
        "benchmark_summary_140_tuning": {
            "p0_cer": tuning_results["P0 RAW"]["mean_cer"],
            "p1_cer": tuning_results["P1 Rotation"]["mean_cer"],
            "p4_cer": tuning_results["P4 Rectified"]["mean_cer"],
            "p6_cer": evaluate_branch_records(p6_final, records, split_role="tuning")["mean_cer"],
        },
        "benchmark_summary_60_held_out_test": {
            "p0_cer": test_results["P0 RAW"]["mean_cer"],
            "p1_cer": test_results["P1 Rotation"]["mean_cer"],
            "p4_cer": test_results["P4 Rectified"]["mean_cer"],
            "p6_final_cer": test_results["P6 Final"]["mean_cer"],
            "p6_final_drug_acc": test_results["P6 Final"]["drug_accuracy"],
            "p6_final_degradation_rate": test_degradations["P6 Final"]["degraded_rate"],
        },
        "selections_200_benchmark": p6_selection_log,
    }

    spec_path = "data/manifests/preprocessing_v1_frozen_spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec_export, f, ensure_ascii=False, indent=2)

    print(f"✅ Exported Preprocessing V1 Frozen Specification to {spec_path}")


if __name__ == "__main__":
    main()

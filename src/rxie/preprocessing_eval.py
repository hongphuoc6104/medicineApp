"""Evaluation metrics for OCR preprocessing ablation benchmark.

Calculates Field-Level Character Error Rate (CER), Word Error Rate (WER),
entity-specific accuracy (Drug Name, Brand, Strength, Quantity), and paired degradation rates (P0 vs Pn).
"""

from __future__ import annotations

import difflib
import glob
import json
import os
import re
import statistics
from dataclasses import dataclass


def edit_distance(ref: list | str, hyp: list | str) -> int:
    """Calculates Levenshtein distance between two sequences."""
    if ref == hyp:
        return 0
    if not ref:
        return len(hyp)
    if not hyp:
        return len(ref)
    matcher = difflib.SequenceMatcher(None, ref, hyp)
    matching = sum(n for _, _, n in matcher.get_matching_blocks())
    return max(len(ref), len(hyp)) - matching


def calculate_item_cer(gold_item: str, ocr_lines: list[str]) -> float:
    """
    Calculates the exact CER of a gold medication entity/line against
    the best-matching candidate line in the OCR output.
    """
    if not gold_item:
        return 0.0
    gold_clean = re.sub(r"\s+", " ", gold_item.strip().lower())
    if not gold_clean:
        return 0.0

    best_dist = len(gold_clean)
    for line in ocr_lines:
        line_clean = re.sub(r"\s+", " ", line.strip().lower())
        if not line_clean:
            continue

        if gold_clean in line_clean or line_clean in gold_clean:
            matcher = difflib.SequenceMatcher(None, gold_clean, line_clean)
            match_len = sum(n for _, _, n in matcher.get_matching_blocks())
            dist = max(0, len(gold_clean) - match_len)
            best_dist = min(best_dist, dist)
            continue

        matcher = difflib.SequenceMatcher(None, gold_clean, line_clean)
        match_len = sum(n for _, _, n in matcher.get_matching_blocks())
        dist = max(len(gold_clean), len(line_clean)) - match_len
        best_dist = min(best_dist, dist)

    return min(1.0, best_dist / len(gold_clean))


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculates standard Character Error Rate (CER)."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    if not hypothesis:
        return 1.0
    if reference == hypothesis:
        return 0.0
    matcher = difflib.SequenceMatcher(None, reference, hypothesis)
    return max(0.0, 1.0 - matcher.ratio())


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculates standard Word Error Rate (WER)."""
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    if not hyp_words:
        return 1.0
    matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
    return max(0.0, 1.0 - matcher.ratio())


def exact_match_accuracy(
    gold_items: list[str], predicted_items: list[str]
) -> float:
    """Calculates exact match percentage for a list of tokens/attributes."""
    if not gold_items:
        return 1.0 if not predicted_items else 0.0
    matches = sum(
        1
        for g, p in zip(gold_items, predicted_items, strict=False)
        if g.strip() == p.strip()
    )
    return matches / max(len(gold_items), len(predicted_items))


@dataclass(frozen=True)
class PreprocessingComparison:
    raw_cer: float
    processed_cer: float
    delta_cer: float  # < 0 means improved, > 0 means degraded
    is_improved: bool
    is_degraded: bool
    is_equal: bool


def compare_paired_ocr(
    gold: str, raw_ocr: str, processed_ocr: str
) -> PreprocessingComparison:
    """Compares RAW OCR (P0) vs Processed OCR (Pn) against manual ground-truth string."""
    raw_cer = calculate_cer(gold, raw_ocr)
    proc_cer = calculate_cer(gold, processed_ocr)
    delta = proc_cer - raw_cer
    return PreprocessingComparison(
        raw_cer=raw_cer,
        processed_cer=proc_cer,
        delta_cer=delta,
        is_improved=delta < -1e-4,
        is_degraded=delta > 1e-4,
        is_equal=abs(delta) <= 1e-4,
    )


def compare_paired_ocr_items(
    gold_items: list[str], raw_lines: list[str], proc_lines: list[str]
) -> PreprocessingComparison:
    """Compares RAW OCR (P0) vs Processed OCR (Pn) item-level CER."""
    raw_cer = statistics.mean([calculate_item_cer(it, raw_lines) for it in gold_items]) if gold_items else 0.0
    proc_cer = statistics.mean([calculate_item_cer(it, proc_lines) for it in gold_items]) if gold_items else 0.0
    delta = proc_cer - raw_cer
    return PreprocessingComparison(
        raw_cer=raw_cer,
        processed_cer=proc_cer,
        delta_cer=delta,
        is_improved=delta < -1e-4,
        is_degraded=delta > 1e-4,
        is_equal=abs(delta) <= 1e-4,
    )


def evaluate_branch_with_benchmark_gt(
    branch_ocr_dir: str,
    benchmark_gt_file: str = "data/manifests/benchmark_200_gt.json",
    split_filter: str | None = None,  # "tuning", "test", or None for all
) -> dict:
    with open(benchmark_gt_file, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    records = gt_data.get("records", {})
    json_files = glob.glob(f"{branch_ocr_dir}/**/*.json", recursive=True)
    ocr_map = {}
    for p in json_files:
        bid = os.path.splitext(os.path.basename(p))[0]
        ocr_map[bid] = p

    cers = []
    drug_accuracies = []
    strength_accuracies = []
    quantity_accuracies = []

    evaluated_count = 0
    for image_id, rec in records.items():
        if split_filter and rec.get("split_role") != split_filter:
            continue

        if image_id not in ocr_map:
            continue

        evaluated_count += 1
        gold_meds = rec.get("medications", [])
        ocr_file = ocr_map[image_id]

        with open(ocr_file, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            lines = [l.get("text", "").strip() for b in d.get("blocks", []) for l in b.get("lines", []) if l.get("text", "").strip()]
            full_ocr_text = " ".join(lines).lower()

        # Build items to evaluate for this image
        gold_items = []
        d_matches = 0
        s_matches = 0
        q_matches = 0

        for m in gold_meds:
            if m.get("drug_raw"):
                gold_items.append(m["drug_raw"])
            if m.get("instruction_raw"):
                gold_items.append(m["instruction_raw"])

            # Field checks
            d_norm = m.get("drug_normalized", "").lower()
            b_norm = m.get("brand_normalized", "").lower()
            if (d_norm and d_norm in full_ocr_text) or (b_norm and b_norm in full_ocr_text) or (m.get("drug_raw", "").lower() in full_ocr_text):
                d_matches += 1

            s_raw = (m.get("strength_raw") or "").lower()
            if s_raw and s_raw in full_ocr_text:
                s_matches += 1

            q_val = str(m.get("quantity_value_raw") or "")
            if q_val and q_val in full_ocr_text:
                q_matches += 1

        img_cer = statistics.mean([calculate_item_cer(it, lines) for it in gold_items]) if gold_items else 0.0
        cers.append(img_cer)

        n_meds = len(gold_meds) if gold_meds else 1
        drug_accuracies.append(d_matches / n_meds)
        strength_accuracies.append(s_matches / n_meds)
        quantity_accuracies.append(q_matches / n_meds)

    return {
        "evaluated_images": evaluated_count,
        "mean_cer": statistics.mean(cers) if cers else 0.0,
        "median_cer": statistics.median(cers) if cers else 0.0,
        "drug_accuracy": statistics.mean(drug_accuracies) if drug_accuracies else 0.0,
        "strength_accuracy": statistics.mean(strength_accuracies) if strength_accuracies else 0.0,
        "quantity_accuracy": statistics.mean(quantity_accuracies) if quantity_accuracies else 0.0,
    }

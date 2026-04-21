"""
Compute OCR proxy metrics (CER/WER) for drug text on curated subset.

Input:
- data/eval/gt_ocr_subset.jsonl
- data/output/eval/latest_eval_run.txt
- data/output/eval/<run>/per_image_detail.jsonl

Usage:
    venv/bin/python scripts/tests/test_phase_a_ocr_metrics.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
OUT_ROOT = ROOT / "data" / "output" / "eval"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    cleaned = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return " ".join("".join(cleaned).split())


def levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def cer(reference: str, hypothesis: str) -> float:
    ref = list(reference)
    hyp = list(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str) -> float:
    ref = reference.split()
    hyp = hypothesis.split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def best_match_for_reference(reference: str, candidates: list[str]) -> tuple[str, float, float]:
    if not candidates:
        return "", 1.0, 1.0
    best_text = ""
    best_cer = float("inf")
    best_wer = float("inf")
    for c in candidates:
        c_norm = normalize(c)
        val_cer = cer(reference, c_norm)
        val_wer = wer(reference, c_norm)
        if (val_cer, val_wer) < (best_cer, best_wer):
            best_text = c_norm
            best_cer = val_cer
            best_wer = val_wer
    return best_text, best_cer, best_wer


def load_alias_map() -> list[tuple[str, str]]:
    payload = json.loads((EVAL_DIR / "canonical_drug_aliases.json").read_text(encoding="utf-8"))
    alias_map = []
    for row in payload["canonical_drugs"]:
        cid = row["canonical_id"]
        for alias in row["aliases"]:
            alias_map.append((cid, normalize(alias)))
    alias_map.sort(key=lambda x: len(x[1]), reverse=True)
    return alias_map


def infer_canonical_ids(text: str, alias_map: list[tuple[str, str]]) -> set[str]:
    norm = normalize(text)
    cids: set[str] = set()
    for cid, alias in alias_map:
        if alias and alias in norm:
            cids.add(cid)
    return cids


def trim_to_reference_shape(candidate: str, reference: str) -> str:
    """Trim candidate to lexical core to reduce dosage/instruction noise.

    We keep alphabetic tokens and limit token count to reference token count.
    """
    cand = normalize(candidate)
    ref = normalize(reference)
    if not cand:
        return ""

    cand_tokens = cand.split()
    alpha_tokens = [
        t
        for t in cand_tokens
        if re.search(r"[a-z]", t)
        and t not in {"mg", "mcg", "g", "ml", "vien", "ong", "goi", "lo"}
    ]
    if not alpha_tokens:
        return ""

    n_ref = max(1, len(ref.split()))
    core = alpha_tokens[:n_ref]
    return " ".join(core)


def main() -> None:
    latest_run = (OUT_ROOT / "latest_eval_run.txt").read_text(encoding="utf-8").strip()
    run_dir = ROOT / latest_run

    detail_path = run_dir / "per_image_detail.jsonl"
    if not detail_path.exists():
        raise FileNotFoundError(f"Missing detail file: {detail_path}")

    pred_map = defaultdict(list)
    with detail_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("mode") != "proposed":
                continue
            image_id = row["image_id"]
            for t in row.get("pred_texts", []):
                if t:
                    pred_map[image_id].append(t)

    alias_map = load_alias_map()

    records = []
    with (EVAL_DIR / "gt_ocr_subset.jsonl").open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            image_id = obj["image_id"]
            ref = normalize(obj["reference_text"])

            same_cid_candidates = [
                c
                for c in pred_map[image_id]
                if obj["canonical_id"] in infer_canonical_ids(c, alias_map)
            ]

            normalized_candidates = [trim_to_reference_shape(c, ref) for c in same_cid_candidates]
            normalized_candidates = [c for c in normalized_candidates if c]

            best_text, best_cer, best_wer = best_match_for_reference(ref, normalized_candidates)
            records.append(
                {
                    "image_id": image_id,
                    "group_id": obj["group_id"],
                    "canonical_id": obj["canonical_id"],
                    "reference_text": ref,
                    "matched_prediction": best_text,
                    "cer": best_cer,
                    "wer": best_wer,
                }
            )

    avg_cer = sum(r["cer"] for r in records) / len(records)
    avg_wer = sum(r["wer"] for r in records) / len(records)

    matched = [r for r in records if r["matched_prediction"]]
    matched_count = len(matched)
    matched_ratio = (matched_count / len(records)) if records else 0.0
    if matched:
        avg_cer_matched = sum(r["cer"] for r in matched) / matched_count
        avg_wer_matched = sum(r["wer"] for r in matched) / matched_count
    else:
        avg_cer_matched = 1.0
        avg_wer_matched = 1.0

    out_json = run_dir / "ocr_metrics.json"
    payload = {
        "generated_at": datetime.now().isoformat(),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "mode": "proposed",
        "sample_count": len(records),
        "matched_count": matched_count,
        "matched_ratio": matched_ratio,
        "avg_cer": avg_cer,
        "avg_wer": avg_wer,
        "avg_cer_matched_only": avg_cer_matched,
        "avg_wer_matched_only": avg_wer_matched,
        "details": records,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    out_csv = run_dir / "ocr_metrics.csv"
    import csv

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "group_id",
                "canonical_id",
                "reference_text",
                "matched_prediction",
                "cer",
                "wer",
            ],
        )
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    **r,
                    "cer": f"{r['cer']:.6f}",
                    "wer": f"{r['wer']:.6f}",
                }
            )

    print(f"PASS: OCR metrics saved to {out_json.relative_to(ROOT)}")
    print(f"- matched: {matched_count}/{len(records)} ({matched_ratio:.2%})")
    print(f"- avg CER: {avg_cer:.4f}")
    print(f"- avg WER: {avg_wer:.4f}")


if __name__ == "__main__":
    main()

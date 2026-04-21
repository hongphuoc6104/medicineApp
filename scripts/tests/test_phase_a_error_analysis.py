"""
Generate structured error analysis from Phase A evaluation artifacts.

Inputs:
- data/output/eval/latest_eval_run.txt
- data/output/eval/<run>/per_image_detail.jsonl

Output:
- data/output/eval/<run>/error_cases.csv
- data/output/eval/<run>/error_analysis.json
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data" / "output" / "eval"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def classify_error(fp: int, fn: int) -> str:
    if fp > 0 and fn > 0:
        return "mixed_fp_fn"
    if fp > 0:
        return "over_extraction_fp"
    if fn > 0:
        return "under_extraction_fn"
    return "exact_match"


def main() -> None:
    latest = (OUT_ROOT / "latest_eval_run.txt").read_text(encoding="utf-8").strip()
    run_dir = ROOT / latest
    detail_file = run_dir / "per_image_detail.jsonl"

    rows = []
    with detail_file.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("mode") != "proposed":
                continue
            fp = int(obj.get("fp", 0))
            fn = int(obj.get("fn", 0))
            category = classify_error(fp, fn)
            rows.append(
                {
                    "image_id": obj["image_id"],
                    "group_id": obj["group_id"],
                    "relative_path": obj["relative_path"],
                    "tp": int(obj.get("tp", 0)),
                    "fp": fp,
                    "fn": fn,
                    "precision": float(obj.get("precision", 0.0)),
                    "recall": float(obj.get("recall", 0.0)),
                    "f1": float(obj.get("f1", 0.0)),
                    "error_category": category,
                    "gt_ids": "|".join(obj.get("gt_ids", [])),
                    "pred_ids": "|".join(obj.get("pred_ids", [])),
                    "pred_texts": " || ".join(obj.get("pred_texts", [])),
                }
            )

    error_rows = [r for r in rows if r["error_category"] != "exact_match"]
    counter = Counter(r["error_category"] for r in rows)
    group_counter = Counter(r["group_id"] for r in error_rows)

    out_csv = run_dir / "error_cases.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "group_id",
                "relative_path",
                "tp",
                "fp",
                "fn",
                "precision",
                "recall",
                "f1",
                "error_category",
                "gt_ids",
                "pred_ids",
                "pred_texts",
            ],
        )
        writer.writeheader()
        for r in error_rows:
            writer.writerow(
                {
                    **r,
                    "precision": f"{r['precision']:.6f}",
                    "recall": f"{r['recall']:.6f}",
                    "f1": f"{r['f1']:.6f}",
                }
            )

    analysis = {
        "generated_at": datetime.now().isoformat(),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "total_images": len(rows),
        "error_images": len(error_rows),
        "error_rate": (len(error_rows) / len(rows)) if rows else 0.0,
        "category_distribution": dict(counter),
        "group_error_distribution": dict(group_counter),
        "top_error_examples": error_rows[:10],
    }

    out_json = run_dir / "error_analysis.json"
    out_json.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PASS: error analysis saved to {out_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

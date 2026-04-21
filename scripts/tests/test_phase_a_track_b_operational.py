"""
Run Track B operational stress metrics on the extended unlabeled pool.

Inputs:
- data/eval_v2/phase_a_manifest_v2.csv
- adaptive Phase A pipeline in core/pipeline.py

Outputs:
- data/output/eval/<run>/track_b_operational.json
- data/output/eval/<run>/track_b_operational.csv

Usage:
    venv/bin/python scripts/tests/test_phase_a_track_b_operational.py
    venv/bin/python scripts/tests/test_phase_a_track_b_operational.py --limit 20
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVAL_V2_DIR = ROOT / "data" / "eval_v2"
OUT_ROOT = ROOT / "data" / "output" / "eval"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = (len(values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1.0 - frac) + values[hi] * frac


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit Track B image count")
    return parser.parse_args()


def load_manifest(limit: int) -> list[dict]:
    rows = []
    with (EVAL_V2_DIR / "phase_a_manifest_v2.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") != "extended_unlabeled":
                continue
            if row.get("include_eval", "").strip().lower() != "yes":
                continue
            rows.append(row)
    rows = sorted(rows, key=lambda r: (r["subset"], r["image_id"]))
    if limit > 0:
        rows = rows[:limit]
    return rows


def main() -> None:
    args = parse_args()
    manifest = load_manifest(args.limit)
    latest = (OUT_ROOT / "latest_eval_run.txt").read_text(encoding="utf-8").strip()
    run_dir = ROOT / latest

    from core.pipeline import MedicinePipeline

    pipe = MedicinePipeline()
    rows = []
    strategy_counter = Counter()
    error_counter = Counter()
    times = []

    for idx, row in enumerate(manifest, start=1):
        image_path = ROOT / row["relative_path"]
        t0 = time.perf_counter()
        result = pipe.scan_prescription_app(str(image_path))
        elapsed = time.perf_counter() - t0

        meds = result.get("medications", []) if isinstance(result, dict) else []
        stats = result.get("stats", {}) if isinstance(result, dict) else {}
        error = result.get("error") if isinstance(result, dict) else "invalid_result"
        strategy = stats.get("selection_strategy", "unknown")

        strategy_counter[strategy] += 1
        if error:
            error_counter[error] += 1
        times.append(elapsed)
        rows.append(
            {
                "image_id": row["image_id"],
                "subset": row["subset"],
                "relative_path": row["relative_path"],
                "elapsed_s": elapsed,
                "medication_count": len(meds),
                "has_output": int(bool(meds)),
                "selection_strategy": strategy,
                "selection_reason": stats.get("selection_reason", ""),
                "error": error or "",
            }
        )
        print(
            f"[{idx:03d}/{len(manifest):03d}] {row['image_id']} meds={len(meds)} "
            f"strategy={strategy} t={elapsed:.2f}s"
        )

    output_count = sum(r["has_output"] for r in rows)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "image_count": len(rows),
        "non_empty_output_rate": (output_count / len(rows)) if rows else 0.0,
        "ocr_empty_error_rate": (
            error_counter.get("OCR found no text", 0) / len(rows)
        ) if rows else 0.0,
        "latency_mean_s": (sum(times) / len(times)) if times else 0.0,
        "latency_p50_s": percentile(times, 0.50),
        "latency_p90_s": percentile(times, 0.90),
        "selection_strategy_distribution": dict(strategy_counter),
        "error_distribution": dict(error_counter),
    }

    out_json = run_dir / "track_b_operational.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    out_csv = run_dir / "track_b_operational.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "subset",
                "relative_path",
                "elapsed_s",
                "medication_count",
                "has_output",
                "selection_strategy",
                "selection_reason",
                "error",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "elapsed_s": f"{row['elapsed_s']:.6f}",
                }
            )

    print(f"PASS: Track B operational metrics saved to {out_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""
Compute bootstrap confidence intervals and paired deltas for Phase A metrics.

Inputs:
- data/output/eval/latest_eval_run.txt
- data/output/eval/<run>/per_image_detail.jsonl

Outputs:
- data/output/eval/<run>/bootstrap_ci.json

Usage:
    venv/bin/python scripts/tests/test_phase_a_bootstrap_ci.py
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data" / "output" / "eval"

BOOTSTRAP_SAMPLES = 2000
SEED = 42


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = (len(values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1.0 - frac) + values[hi] * frac


def summarize_rows(rows: list[dict]) -> dict:
    tp = sum(int(r.get("tp", 0)) for r in rows)
    fp = sum(int(r.get("fp", 0)) for r in rows)
    fn = sum(int(r.get("fn", 0)) for r in rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    exact = sum(1 for r in rows if bool(r.get("exact_match")))
    exact_rate = exact / len(rows) if rows else 0.0
    latencies = [float(r.get("elapsed_s", 0.0)) for r in rows]
    latency_mean = sum(latencies) / len(latencies) if latencies else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match_rate": exact_rate,
        "latency_mean_s": latency_mean,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def bootstrap_mode(rows: list[dict], rng: random.Random) -> dict:
    if not rows:
        return {}

    stats = defaultdict(list)
    n = len(rows)
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        summary = summarize_rows(sample)
        for key in ("precision", "recall", "f1", "exact_match_rate", "latency_mean_s"):
            stats[key].append(summary[key])

    point = summarize_rows(rows)
    return {
        "point_estimate": point,
        "bootstrap": {
            key: {
                "mean": sum(values) / len(values),
                "ci95": [percentile(values, 0.025), percentile(values, 0.975)],
            }
            for key, values in stats.items()
        },
    }


def bootstrap_paired_delta(rows_a: list[dict], rows_b: list[dict], rng: random.Random) -> dict:
    by_id_a = {row["image_id"]: row for row in rows_a}
    by_id_b = {row["image_id"]: row for row in rows_b}
    common_ids = sorted(set(by_id_a) & set(by_id_b))
    paired_a = [by_id_a[i] for i in common_ids]
    paired_b = [by_id_b[i] for i in common_ids]
    n = len(common_ids)
    if n == 0:
        return {}

    deltas = defaultdict(list)
    for _ in range(BOOTSTRAP_SAMPLES):
        sample_a = []
        sample_b = []
        for _ in range(n):
            idx = rng.randrange(n)
            sample_a.append(paired_a[idx])
            sample_b.append(paired_b[idx])
        summary_a = summarize_rows(sample_a)
        summary_b = summarize_rows(sample_b)
        for key in ("precision", "recall", "f1", "exact_match_rate", "latency_mean_s"):
            deltas[key].append(summary_a[key] - summary_b[key])

    point_a = summarize_rows(paired_a)
    point_b = summarize_rows(paired_b)
    return {
        "image_count": n,
        "point_delta": {
            key: point_a[key] - point_b[key]
            for key in ("precision", "recall", "f1", "exact_match_rate", "latency_mean_s")
        },
        "bootstrap": {
            key: {
                "mean": sum(values) / len(values),
                "ci95": [percentile(values, 0.025), percentile(values, 0.975)],
            }
            for key, values in deltas.items()
        },
    }


def main() -> None:
    latest = (OUT_ROOT / "latest_eval_run.txt").read_text(encoding="utf-8").strip()
    run_dir = ROOT / latest
    detail_path = run_dir / "per_image_detail.jsonl"

    by_mode: dict[str, list[dict]] = defaultdict(list)
    with detail_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            by_mode[row["mode"]].append(row)

    rng = random.Random(SEED)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "seed": SEED,
        "modes": {mode: bootstrap_mode(rows, rng) for mode, rows in sorted(by_mode.items())},
        "paired_deltas": {},
    }

    comparisons = [
        ("proposed", "baseline_no_stt"),
        ("proposed", "forced_stt"),
    ]
    for left, right in comparisons:
        if left in by_mode and right in by_mode:
            payload["paired_deltas"][f"{left}_minus_{right}"] = bootstrap_paired_delta(
                by_mode[left],
                by_mode[right],
                rng,
            )

    out_json = run_dir / "bootstrap_ci.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: bootstrap CIs saved to {out_json.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

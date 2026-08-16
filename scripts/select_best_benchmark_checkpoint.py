#!/usr/bin/env python3
"""
Hyperparameter Selection & Checkpoint Promotion Script for RxIE Benchmark V1.
Compares all validation results in experiments/<model>/tuning/ for each seed,
identifies the best hyperparameter (learning rate), and promotes the best checkpoint
for final sealed test split evaluation.

Usage:
  python scripts/select_best_benchmark_checkpoint.py --model E0_phobert
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="RxIE Hyperparameter Selection & Checkpoint Promotion")
    parser.add_argument("--model", type=str, default="E0_phobert", choices=["E0_phobert", "E1_bamibert", "E2_vipubmeddeberta"])
    parser.add_argument("--experiments-dir", type=Path, default=root_dir / "experiments")
    parser.add_argument("--promote", action="store_true", help="Promote best tuning checkpoints to experiments/<model>/final/")

    args = parser.parse_args()
    model_dir = args.experiments_dir / args.model
    tuning_dir = model_dir / "tuning"

    if not tuning_dir.exists():
        print(f"[!] No tuning directory found at {tuning_dir}. Run hyperparameter tuning first.")
        sys.exit(1)

    # Collect all tuning runs
    runs: list[dict[str, Any]] = []
    for run_path in tuning_dir.iterdir():
        if not run_path.is_dir():
            continue
        manifest_path = run_path / "checkpoint_manifest.json"
        metrics_path = run_path / "metrics_val.json"

        if manifest_path.exists() and metrics_path.exists():
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
            with metrics_path.open("r", encoding="utf-8") as f:
                metrics = json.load(f)

            rx_macro_f1 = metrics.get("prescription_macro_summary", {}).get("prescription_macro_entity_f1", 0.0)
            micro_f1 = metrics.get("entity_micro", {}).get("f1", 0.0)
            active_macro_f1 = metrics.get("entity_macro", {}).get("f1", 0.0)

            runs.append({
                "path": run_path,
                "seed": manifest.get("seed"),
                "learning_rate": manifest.get("learning_rate"),
                "best_epoch": manifest.get("best_epoch"),
                "rx_macro_f1": rx_macro_f1,
                "micro_f1": micro_f1,
                "active_macro_f1": active_macro_f1,
                "manifest": manifest,
            })

    if not runs:
        print(f"[!] No valid tuning runs found with manifests in {tuning_dir}.")
        sys.exit(1)

    print("==================================================")
    print(f"   RxIE Hyperparameter Selection: {args.model}   ")
    print("==================================================")
    print(f"{'Run Directory':<40} {'Seed':<6} {'LR':<10} {'Best Ep':<8} {'Rx-Macro F1':<12} {'Micro F1':<10}")
    print("-" * 90)

    for r in sorted(runs, key=lambda x: (x["seed"], -x["rx_macro_f1"])):
        print(f"{r['path'].name:<40} {r['seed']:<6} {r['learning_rate']:<10} {r['best_epoch']:<8} {r['rx_macro_f1']:<12.4f} {r['micro_f1']:<10.4f}")

    # Group by seed and find best run per seed
    seeds = sorted({r["seed"] for r in runs})
    best_per_seed: dict[int, dict[str, Any]] = {}

    for s in seeds:
        seed_runs = [r for r in runs if r["seed"] == s]
        best_run = max(seed_runs, key=lambda x: (x["rx_macro_f1"], x["micro_f1"]))
        best_per_seed[s] = best_run

    print("==================================================")
    print("                BEST RUNS PER SEED                ")
    print("==================================================")
    for s, br in best_per_seed.items():
        print(f"Seed {s}: LR={br['learning_rate']} (Rx-Macro F1={br['rx_macro_f1']:.4f}, Micro F1={br['micro_f1']:.4f}) -> {br['path'].name}")

    if args.promote:
        final_dir = model_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        print("\n[*] Promoting selected checkpoints to final evaluation directory...")

        for s, br in best_per_seed.items():
            dest_dir = final_dir / f"seed_{s}"
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(br["path"], dest_dir)

            # Update manifest in destination to reflect validated promotion
            dest_manifest_path = dest_dir / "checkpoint_manifest.json"
            with dest_manifest_path.open("r", encoding="utf-8") as f:
                dest_manifest = json.load(f)

            dest_manifest["run_type"] = "final"
            dest_manifest["selected_on_validation"] = True
            dest_manifest["eligible_for_final_test"] = True
            dest_manifest["promoted_from_tuning_run"] = br["path"].name

            with dest_manifest_path.open("w", encoding="utf-8") as f:
                json.dump(dest_manifest, f, ensure_ascii=False, indent=2)

            print(f"[+] Promoted Seed {s} -> {dest_dir} (Eligible for Test: YES)")

    print("==================================================")


if __name__ == "__main__":
    main()

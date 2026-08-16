#!/usr/bin/env python3
"""Select one benchmark learning rate across the complete tuning seed grid."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from rxie.benchmark_protocol import (  # noqa: E402
    SELECTION_SCHEMA_VERSION,
    payload_sha256,
    select_global_learning_rate,
    sha256_file,
    validate_selection_manifest,
)


def collect_tuning_candidates(
    *,
    model_id: str,
    experiments_dir: Path,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []
    tuning_dir = experiments_dir / model_id / "tuning"
    for learning_rate in config["hyperparameters"]["learning_rates"]:
        for seed in config["seeds"]:
            run_name = f"lr_{float(learning_rate):.1e}_seed_{int(seed)}"
            run_dir = tuning_dir / run_name
            manifest_path = run_dir / "checkpoint_manifest.json"
            metrics_path = run_dir / "metrics_val.json"
            if not manifest_path.is_file() or not metrics_path.is_file():
                raise FileNotFoundError(f"Missing tuning artifacts for {run_name}")

            with manifest_path.open("r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            with metrics_path.open("r", encoding="utf-8") as handle:
                metrics = json.load(handle)

            if manifest.get("run_type") != "tuning":
                raise ValueError(f"Candidate {run_name} is not a tuning run")
            if manifest.get("model_id") != model_id:
                raise ValueError(f"Candidate {run_name} model mismatch")
            if int(manifest.get("seed", -1)) != int(seed):
                raise ValueError(f"Candidate {run_name} seed mismatch")
            if float(manifest.get("learning_rate", -1)) != float(learning_rate):
                raise ValueError(f"Candidate {run_name} learning-rate mismatch")
            if manifest.get("dataset_version") != config["dataset_version"]:
                raise ValueError(f"Candidate {run_name} dataset mismatch")

            primary = metrics["prescription_macro_summary"][
                "prescription_macro_entity_f1"
            ]
            secondary = metrics["entity_micro"]["f1"]
            if primary is None:
                raise ValueError(
                    f"Candidate {run_name} has no informative prescription metric"
                )
            if float(manifest.get("best_validation_metric")) != float(primary):
                raise ValueError(f"Candidate {run_name} manifest/metrics mismatch")

            try:
                run_path = str(run_dir.resolve().relative_to(root_dir.resolve()))
            except ValueError:
                run_path = str(run_dir.resolve())
            candidates.append(
                {
                    "seed": int(seed),
                    "learning_rate": float(learning_rate),
                    "primary_metric": float(primary),
                    "secondary_metric": float(secondary),
                    "run_path": run_path,
                    "checkpoint_manifest_sha256": sha256_file(manifest_path),
                    "metrics_val_sha256": sha256_file(metrics_path),
                    "source_git_commit": manifest.get("source_git_commit"),
                }
            )
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="RxIE global learning-rate selection")
    parser.add_argument(
        "--model",
        required=True,
        choices=["E0_phobert", "E1_bamibert", "E2_vipubmeddeberta"],
    )
    parser.add_argument(
        "--config", type=Path, default=root_dir / "configs" / "benchmark_v1.yaml"
    )
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    candidates = collect_tuning_candidates(
        model_id=args.model,
        experiments_dir=root_dir / "experiments",
        config=config,
    )
    aggregates, selected_lr = select_global_learning_rate(
        candidates,
        seeds=[int(seed) for seed in config["seeds"]],
        learning_rates=[
            float(lr) for lr in config["hyperparameters"]["learning_rates"]
        ],
    )

    output_path = root_dir / config["selection"]["manifest_path_template"].format(
        model=args.model
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"Selection manifest already exists: {output_path}")

    selection_manifest = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "protocol_version": config["protocol_version"],
        "model_id": args.model,
        "dataset_version": config["dataset_version"],
        "config_sha256": sha256_file(args.config),
        "primary_metric": config["model_selection"]["primary_metric"],
        "secondary_metric": config["model_selection"]["secondary_metric"],
        "seeds": [int(seed) for seed in config["seeds"]],
        "learning_rates": [
            float(lr) for lr in config["hyperparameters"]["learning_rates"]
        ],
        "candidates": candidates,
        "aggregates": aggregates,
        "selected_lr": selected_lr,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    selection_manifest["payload_sha256"] = payload_sha256(selection_manifest)
    validate_selection_manifest(
        selection_manifest,
        config=config,
        config_path=args.config,
        model_id=args.model,
        repository_root=root_dir,
    )
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(
            selection_manifest, handle, ensure_ascii=True, allow_nan=False, indent=2
        )
        handle.write("\n")

    print("LR          Rx-Macro mean    SD          Micro mean")
    for row in aggregates:
        print(
            f"{row['learning_rate']:<11.1e} {row['primary_mean']:<16.6f} "
            f"{row['primary_std']:<11.6f} {row['secondary_mean']:.6f}"
        )
    print(f"selected_lr = {selected_lr:.1e}")
    print(f"selection_manifest = {output_path}")


if __name__ == "__main__":
    main()

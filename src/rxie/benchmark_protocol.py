"""Shared, fail-closed benchmark selection and authorization contracts."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

SELECTION_SCHEMA_VERSION = "rxie.selection_manifest.v1"
BENCHMARK_IMPLEMENTATION_FILES = (
    "configs/benchmark_v1.yaml",
    "docs/BENCHMARK_PROTOCOL_V1.md",
    "scripts/train_token_ner.py",
    "src/rxie/benchmark_protocol.py",
    "src/rxie/chunking.py",
    "src/rxie/evaluation.py",
    "src/rxie/tokenization.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(file_path)))
    return digest.hexdigest()


def benchmark_implementation_sha256(repository_root: Path) -> str:
    digest = hashlib.sha256()
    for relative_path in BENCHMARK_IMPLEMENTATION_FILES:
        path = repository_root / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Missing benchmark implementation file: {path}")
        digest.update(relative_path.encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def payload_sha256(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "payload_sha256"}
    encoded = json.dumps(
        unsigned,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def select_global_learning_rate(
    candidates: list[dict[str, Any]],
    *,
    seeds: list[int],
    learning_rates: list[float],
) -> tuple[list[dict[str, Any]], float]:
    """Validate a complete LR x seed grid and select one LR globally."""
    expected = {(int(seed), float(lr)) for seed in seeds for lr in learning_rates}
    actual = {(int(row["seed"]), float(row["learning_rate"])) for row in candidates}
    if len(actual) != len(candidates):
        raise ValueError("Duplicate tuning seed/LR candidate")
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"Incomplete tuning grid; missing={missing}, extra={extra}")

    aggregates = []
    for learning_rate in learning_rates:
        rows = sorted(
            (
                row
                for row in candidates
                if float(row["learning_rate"]) == float(learning_rate)
            ),
            key=lambda row: int(row["seed"]),
        )
        primary = [float(row["primary_metric"]) for row in rows]
        secondary = [float(row["secondary_metric"]) for row in rows]
        if not all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in primary + secondary
        ):
            raise ValueError("Selection metrics must be finite values in [0, 1]")
        aggregates.append(
            {
                "learning_rate": float(learning_rate),
                "primary_mean": statistics.fmean(primary),
                "primary_std": statistics.stdev(primary),
                "secondary_mean": statistics.fmean(secondary),
                "secondary_std": statistics.stdev(secondary),
                "seed_values": [
                    {
                        "seed": int(row["seed"]),
                        "primary": float(row["primary_metric"]),
                        "secondary": float(row["secondary_metric"]),
                    }
                    for row in rows
                ],
            }
        )

    selected = min(
        aggregates,
        key=lambda row: (
            -row["primary_mean"],
            -row["secondary_mean"],
            row["primary_std"],
            row["learning_rate"],
        ),
    )
    return aggregates, float(selected["learning_rate"])


def validate_selection_manifest(
    manifest: dict[str, Any],
    *,
    config: dict[str, Any],
    config_path: Path,
    model_id: str,
    repository_root: Path,
) -> float:
    """Recompute and validate a selector-produced manifest."""
    if manifest.get("schema_version") != SELECTION_SCHEMA_VERSION:
        raise ValueError("Unsupported selection manifest schema")
    if manifest.get("protocol_version") != config["protocol_version"]:
        raise ValueError("Selection protocol version mismatch")
    if manifest.get("model_id") != model_id:
        raise ValueError("Selection model mismatch")
    if manifest.get("dataset_version") != config["dataset_version"]:
        raise ValueError("Selection dataset version mismatch")
    if manifest.get("config_sha256") != sha256_file(config_path):
        raise ValueError("Selection config checksum mismatch")
    if manifest.get("payload_sha256") != payload_sha256(manifest):
        raise ValueError("Selection manifest payload checksum mismatch")

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Selection candidates are missing")
    model_config = config["models"][model_id]
    implementation_hash = benchmark_implementation_sha256(repository_root)
    for candidate in candidates:
        seed = int(candidate["seed"])
        learning_rate = float(candidate["learning_rate"])
        expected_run = (
            repository_root
            / "experiments"
            / model_id
            / "tuning"
            / f"lr_{learning_rate:.1e}_seed_{seed}"
        )
        try:
            expected_relative = str(
                expected_run.resolve().relative_to(repository_root.resolve())
            )
        except ValueError as exc:
            raise ValueError("Tuning artifact path escapes repository") from exc
        if candidate.get("run_path") != expected_relative:
            raise ValueError("Selection candidate path is not canonical")
        checkpoint_manifest_path = expected_run / "checkpoint_manifest.json"
        metrics_path = expected_run / "metrics_val.json"
        environment_path = expected_run / "environment.json"
        if not checkpoint_manifest_path.is_file() or not metrics_path.is_file():
            raise ValueError("Selection candidate artifacts are missing")
        if sha256_file(checkpoint_manifest_path) != candidate.get(
            "checkpoint_manifest_sha256"
        ):
            raise ValueError("Selection candidate checkpoint manifest was modified")
        if sha256_file(metrics_path) != candidate.get("metrics_val_sha256"):
            raise ValueError("Selection candidate metrics were modified")
        with checkpoint_manifest_path.open("r", encoding="utf-8") as handle:
            checkpoint_manifest = json.load(handle)
        with metrics_path.open("r", encoding="utf-8") as handle:
            metrics = json.load(handle)
        if not environment_path.is_file() or sha256_file(
            environment_path
        ) != checkpoint_manifest.get("environment_sha256"):
            raise ValueError("Selection candidate environment provenance mismatch")
        required_manifest_values = {
            "manifest_schema_version": "rxie.checkpoint_manifest.v2",
            "protocol_version": config["protocol_version"],
            "run_type": "tuning",
            "model_id": model_id,
            "seed": seed,
            "learning_rate": learning_rate,
            "dataset_version": config["dataset_version"],
            "config_sha256": sha256_file(config_path),
            "max_input_tokens": int(model_config["max_input_tokens"]),
            "content_overlap": int(config["hyperparameters"]["content_overlap"]),
            "active_entity_types": list(config["token_ner"]["active_entity_types"]),
            "num_labels": int(config["token_ner"]["num_labels"]),
            "backbone_id": model_config["backbone_id"],
            "backbone_revision": model_config["backbone_revision"],
            "tokenizer_id": model_config["tokenizer_id"],
            "tokenizer_revision": model_config["tokenizer_revision"],
            "batch_size": int(config["hyperparameters"]["batch_size"]),
            "epochs_max": int(config["hyperparameters"]["epochs_max"]),
            "weight_decay": float(config["hyperparameters"]["weight_decay"]),
            "warmup_ratio": float(config["hyperparameters"]["warmup_ratio"]),
            "sampling_policy": config["sampling"]["policy"],
            "benchmark_implementation_sha256": implementation_hash,
        }
        for key, expected_value in required_manifest_values.items():
            if checkpoint_manifest.get(key) != expected_value:
                raise ValueError(f"Selection candidate manifest mismatch: {key}")
        if checkpoint_manifest.get("source_git_dirty") is not False:
            raise ValueError("Selection candidate came from a dirty source tree")
        if candidate.get("source_git_commit") != checkpoint_manifest.get(
            "source_git_commit"
        ):
            raise ValueError("Selection candidate source commit mismatch")
        primary = metrics["prescription_macro_summary"]["prescription_macro_entity_f1"]
        secondary = metrics["entity_micro"]["f1"]
        if (
            float(primary) != float(candidate["primary_metric"])
            or float(secondary) != float(candidate["secondary_metric"])
            or float(checkpoint_manifest["best_validation_metric"]) != float(primary)
        ):
            raise ValueError("Selection candidate metric values do not match artifacts")

    if len({candidate.get("source_git_commit") for candidate in candidates}) != 1:
        raise ValueError("Tuning candidates must share one source commit")

    aggregates, selected_lr = select_global_learning_rate(
        candidates,
        seeds=[int(seed) for seed in config["seeds"]],
        learning_rates=[
            float(lr) for lr in config["hyperparameters"]["learning_rates"]
        ],
    )
    if manifest.get("aggregates") != aggregates:
        raise ValueError("Selection aggregates do not match candidate metrics")
    if float(manifest.get("selected_lr", -1)) != selected_lr:
        raise ValueError(
            "Selection manifest does not contain the deterministic global LR"
        )
    return selected_lr


def load_and_validate_selection_manifest(
    path: Path,
    *,
    config: dict[str, Any],
    config_path: Path,
    model_id: str,
    repository_root: Path,
) -> tuple[dict[str, Any], float]:
    if not path.is_file():
        raise FileNotFoundError(f"Selection manifest not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    selected_lr = validate_selection_manifest(
        manifest,
        config=config,
        config_path=config_path,
        model_id=model_id,
        repository_root=repository_root,
    )
    return manifest, selected_lr

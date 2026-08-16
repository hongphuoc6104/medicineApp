#!/usr/bin/env python3
# ruff: noqa: E402
"""Fail-closed evaluator for a complete Protocol-B official run cohort."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))
sys.path.insert(0, str(root_dir))
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
)

from rxie.benchmark_protocol import (
    benchmark_implementation_sha256,
    load_and_validate_selection_manifest,
    sha256_directory,
    sha256_file,
)
from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import AnnotationDocumentV2


def require_clean_source(expected_commit: str) -> None:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty or commit != expected_commit:
        raise PermissionError(
            "Official Test evaluation requires the clean official training commit"
        )


def set_deterministic_inference(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


def authorize_official_checkpoint(
    checkpoint_dir: Path,
    manifest: dict[str, Any],
    *,
    config: dict[str, Any],
    config_path: Path,
    repository_root: Path,
) -> dict[str, Any]:
    """Authorize without opening or checking any sealed test content."""
    if manifest.get("manifest_schema_version") != "rxie.checkpoint_manifest.v2":
        raise PermissionError("Checkpoint manifest schema is not official")
    if manifest.get("run_type") != "official":
        raise PermissionError("Only fresh Protocol-B official runs may access Test")
    if manifest.get("protocol_version") != config["protocol_version"]:
        raise PermissionError("Checkpoint protocol version mismatch")

    model_id = manifest.get("model_id")
    seed = manifest.get("seed")
    if model_id not in config["models"] or seed not in config["seeds"]:
        raise PermissionError("Checkpoint model or seed is outside the frozen protocol")
    expected_dir = (
        repository_root / "experiments" / model_id / "official" / f"seed_{seed}"
    )
    if checkpoint_dir.resolve() != expected_dir.resolve():
        raise PermissionError(f"Official checkpoint must be located at {expected_dir}")

    selection_relative = manifest.get("selection_manifest_path")
    if (
        not selection_relative
        or Path(selection_relative).is_absolute()
        or ".." in Path(selection_relative).parts
    ):
        raise PermissionError(
            "Official checkpoint has no safe selection-manifest reference"
        )
    selection_path = repository_root / selection_relative
    if sha256_file(selection_path) != manifest.get("selection_manifest_sha256"):
        raise PermissionError("Selection manifest checksum mismatch")
    selection, selected_lr = load_and_validate_selection_manifest(
        selection_path,
        config=config,
        config_path=config_path,
        model_id=model_id,
        repository_root=repository_root,
    )
    if float(manifest.get("learning_rate", -1)) != selected_lr:
        raise PermissionError("Official run does not use the globally selected LR")

    release_path = repository_root / "data" / "ner_dataset" / "release_manifest.json"
    with release_path.open("r", encoding="utf-8") as handle:
        release = json.load(handle)
    model_config = config["models"][model_id]
    labels = ["O"]
    for entity_type in config["token_ner"]["active_entity_types"]:
        labels.extend([f"B-{entity_type}", f"I-{entity_type}"])
    expected_values = {
        "source_git_dirty": False,
        "config_sha256": sha256_file(config_path),
        "dataset_version": release["dataset_version"],
        "max_input_tokens": int(model_config["max_input_tokens"]),
        "content_overlap": int(config["hyperparameters"]["content_overlap"]),
        "active_entity_types": list(config["token_ner"]["active_entity_types"]),
        "num_labels": int(config["token_ner"]["num_labels"]),
        "labels": labels,
        "backbone_id": model_config["backbone_id"],
        "backbone_revision": model_config["backbone_revision"],
        "tokenizer_id": model_config["tokenizer_id"],
        "tokenizer_revision": model_config["tokenizer_revision"],
        "batch_size": int(config["hyperparameters"]["batch_size"]),
        "epochs_max": int(config["hyperparameters"]["epochs_max"]),
        "weight_decay": float(config["hyperparameters"]["weight_decay"]),
        "warmup_ratio": float(config["hyperparameters"]["warmup_ratio"]),
        "sampling_policy": config["sampling"]["policy"],
        "benchmark_implementation_sha256": benchmark_implementation_sha256(
            repository_root
        ),
    }
    for key, expected_value in expected_values.items():
        if manifest.get(key) != expected_value:
            raise PermissionError(f"Official checkpoint contract mismatch: {key}")
    if manifest.get("dataset_checksums") != {
        "train.jsonl": release["file_checksums_sha256"]["train.jsonl"],
        "val.jsonl": release["file_checksums_sha256"]["val.jsonl"],
        "test.jsonl": release["file_checksums_sha256"]["test.jsonl"],
    }:
        raise PermissionError("Official checkpoint dataset checksums mismatch")
    for official_seed in config["seeds"]:
        sibling_path = (
            repository_root
            / "experiments"
            / model_id
            / "official"
            / f"seed_{official_seed}"
            / "checkpoint_manifest.json"
        )
        if not sibling_path.is_file():
            raise PermissionError(
                "All three official seeds must finish before Test is unsealed"
            )
        with sibling_path.open("r", encoding="utf-8") as handle:
            sibling = json.load(handle)
        if any(
            sibling.get(key) != expected_value
            for key, expected_value in expected_values.items()
        ):
            raise PermissionError(
                "Official sibling contract is incomplete or malformed"
            )
        if (
            sibling.get("manifest_schema_version") != "rxie.checkpoint_manifest.v2"
            or sibling.get("protocol_version") != config["protocol_version"]
            or sibling.get("run_type") != "official"
            or sibling.get("model_id") != model_id
            or sibling.get("seed") != official_seed
            or sibling.get("selection_manifest_sha256")
            != manifest.get("selection_manifest_sha256")
            or sibling.get("selection_manifest_path")
            != manifest.get("selection_manifest_path")
            or float(sibling.get("learning_rate", -1)) != selected_lr
            or sibling.get("source_git_commit") != manifest.get("source_git_commit")
            or sibling.get("dataset_checksums") != manifest.get("dataset_checksums")
            or sibling.get("backbone_revision") != manifest.get("backbone_revision")
            or sibling.get("tokenizer_revision") != manifest.get("tokenizer_revision")
            or sibling.get("max_input_tokens") != manifest.get("max_input_tokens")
            or sibling.get("content_overlap") != manifest.get("content_overlap")
            or sibling.get("benchmark_implementation_sha256")
            != manifest.get("benchmark_implementation_sha256")
        ):
            raise PermissionError("Official run cohort is inconsistent")
        best_checkpoint = sibling_path.parent / "best_checkpoint"
        environment_path = sibling_path.parent / "environment.json"
        if not best_checkpoint.is_dir():
            raise PermissionError("Official run cohort has a missing checkpoint")
        if sha256_directory(best_checkpoint) != sibling.get("best_checkpoint_sha256"):
            raise PermissionError("Official checkpoint weights were modified")
        if not environment_path.is_file() or sha256_file(
            environment_path
        ) != sibling.get("environment_sha256"):
            raise PermissionError("Official environment provenance was modified")
    return selection


def run_test_inference(
    checkpoint_dir: Path,
    manifest: dict[str, Any],
    test_docs: list[AnnotationDocumentV2],
    device: torch.device,
) -> list[AnnotationDocumentV2]:
    from scripts.train_token_ner import RxieTokenDataset, decode_all_predictions

    best_checkpoint = checkpoint_dir / "best_checkpoint"
    if not best_checkpoint.is_dir():
        raise FileNotFoundError(f"Missing trained model directory: {best_checkpoint}")
    labels = manifest["labels"]
    label_to_id = {label: idx for idx, label in enumerate(labels)}
    id_to_label = {idx: label for idx, label in enumerate(labels)}
    tokenizer = AutoTokenizer.from_pretrained(best_checkpoint)
    model = AutoModelForTokenClassification.from_pretrained(best_checkpoint).to(device)
    model.eval()

    dataset = RxieTokenDataset(
        test_docs,
        tokenizer,
        label_to_id,
        max_input_tokens=int(manifest["max_input_tokens"]),
        content_overlap=int(manifest["content_overlap"]),
    )
    collator = DataCollatorForTokenClassification(tokenizer=tokenizer, padding=True)
    dataloader = DataLoader(
        dataset,
        batch_size=int(manifest["batch_size"]),
        shuffle=False,
        collate_fn=collator,
    )
    all_logits: list[list[list[float]]] = []
    with torch.no_grad():
        for batch in dataloader:
            outputs = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            )
            for index in range(outputs.logits.shape[0]):
                actual_len = int(batch["attention_mask"][index].sum().item())
                all_logits.append(outputs.logits[index, :actual_len].cpu().tolist())
    return decode_all_predictions(test_docs, dataset, all_logits, id_to_label)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official sealed Test evaluator")
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    manifest_path = args.checkpoint_dir / "checkpoint_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing checkpoint manifest: {manifest_path}")
    config_path = root_dir / "configs" / "benchmark_v1.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    require_clean_source(str(manifest.get("source_git_commit", "")))
    authorize_official_checkpoint(
        args.checkpoint_dir,
        manifest,
        config=config,
        config_path=config_path,
        repository_root=root_dir,
    )

    predictions_path = args.checkpoint_dir / "predictions_test.jsonl"
    metrics_path = args.checkpoint_dir / "metrics_test.json"
    if predictions_path.exists() or metrics_path.exists():
        raise FileExistsError("Official Test outputs are immutable and already exist")

    lock_path = args.checkpoint_dir / "test_evaluation.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise FileExistsError(
            "Official Test evaluation is already running or completed"
        ) from exc
    with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_handle:
        lock_handle.write(f"RUNNING {datetime.now(timezone.utc).isoformat()}\n")

    set_deterministic_inference(int(manifest["seed"]))

    release_manifest_path = root_dir / "data" / "ner_dataset" / "release_manifest.json"
    with release_manifest_path.open("r", encoding="utf-8") as handle:
        release_manifest = json.load(handle)
    test_path = root_dir / config["splits"]["test_file"]
    expected_checksum = release_manifest["file_checksums_sha256"]["test.jsonl"]
    if sha256_file(test_path) != expected_checksum:
        raise PermissionError("Sealed Test checksum mismatch")

    with test_path.open("r", encoding="utf-8") as handle:
        gold_docs = [
            AnnotationDocumentV2.model_validate_json(line)
            for line in handle
            if line.strip()
        ]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pred_docs = run_test_inference(args.checkpoint_dir, manifest, gold_docs, device)
    report = evaluate_structured_annotations(
        gold_docs,
        pred_docs,
        active_entity_types=manifest["active_entity_types"],
        task_type="token_ner",
    )

    with predictions_path.open("x", encoding="utf-8") as handle:
        for doc in pred_docs:
            handle.write(
                json.dumps(doc.model_dump(mode="json"), ensure_ascii=False) + "\n"
            )
    with metrics_path.open("x", encoding="utf-8") as handle:
        json.dump(
            report.model_dump(mode="json"),
            handle,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
        handle.write("\n")
    evaluation_manifest_path = args.checkpoint_dir / "evaluation_manifest.json"
    evaluation_manifest = {
        "schema_version": "rxie.test_evaluation.v1",
        "checkpoint_manifest_sha256": sha256_file(manifest_path),
        "best_checkpoint_sha256": manifest["best_checkpoint_sha256"],
        "selection_manifest_sha256": manifest["selection_manifest_sha256"],
        "test_sha256": expected_checksum,
        "predictions_test_sha256": sha256_file(predictions_path),
        "metrics_test_sha256": sha256_file(metrics_path),
        "evaluator_source_git_commit": manifest["source_git_commit"],
        "benchmark_implementation_sha256": manifest["benchmark_implementation_sha256"],
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version()
        if torch.cuda.is_available()
        else None,
        "device_name": torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "CPU",
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with evaluation_manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(
            evaluation_manifest, handle, ensure_ascii=True, allow_nan=False, indent=2
        )
        handle.write("\n")
    lock_path.write_text("COMPLETED\n", encoding="utf-8")

    print(f"Strict Entity Micro F1: {report.entity_micro.f1:.4f}")
    print(f"Active Entity Macro F1: {report.entity_macro.f1:.4f}")
    print(
        "Prescription Macro F1: "
        f"{report.prescription_macro_summary['prescription_macro_entity_f1']:.4f}"
    )


if __name__ == "__main__":
    main()

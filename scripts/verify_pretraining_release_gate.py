#!/usr/bin/env python3
"""Behavioral, seal-safe pre-training gate for Benchmark Protocol v1.2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from rxie.alignment import DEFAULT_ACTIVE_ENTITY_TYPES, build_label_map  # noqa: E402
from rxie.benchmark_protocol import sha256_file  # noqa: E402
from rxie.schemas import AnnotationDocumentV2  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_unsealed(path: Path) -> list[AnnotationDocumentV2]:
    with path.open("r", encoding="utf-8") as handle:
        return [
            AnnotationDocumentV2.model_validate_json(line)
            for line in handle
            if line.strip()
        ]


def run_hardened_release_gate() -> dict[str, Any]:
    dataset_dir = root_dir / "data" / "ner_dataset"
    release_path = dataset_dir / "release_manifest.json"
    config_path = root_dir / "configs" / "benchmark_v1.yaml"
    protocol_path = root_dir / "docs" / "BENCHMARK_PROTOCOL_V1.md"
    with release_path.open("r", encoding="utf-8") as handle:
        release = json.load(handle)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    require(
        config["protocol_version"] == "rxie.benchmark_protocol.v1.2.0",
        "Protocol is not v1.2",
    )
    require(
        config["official_protocol"] == "B",
        "Official protocol must be fresh-run Protocol B",
    )
    require(
        config["dataset_version"] == release["dataset_version"],
        "Dataset version mismatch",
    )
    for filename in ["train.jsonl", "val.jsonl", "bio_train.jsonl", "bio_val.jsonl"]:
        require(
            sha256_file(dataset_dir / filename)
            == release["file_checksums_sha256"][filename],
            f"Unsealed dataset checksum mismatch: {filename}",
        )
    for quality_gate in [
        "zero_leakage_isolation",
        "zero_overlap_spans",
        "zero_span_boundary_errors",
    ]:
        require(
            release["quality_gates"].get(quality_gate) is True,
            f"Release quality gate failed: {quality_gate}",
        )

    train_docs = _load_unsealed(dataset_dir / "train.jsonl")
    val_docs = _load_unsealed(dataset_dir / "val.jsonl")
    require(
        len(train_docs) == release["document_counts"]["train"] == 279,
        "Train count mismatch",
    )
    require(
        len(val_docs) == release["document_counts"]["val"] == 115,
        "Validation count mismatch",
    )
    require(
        release["document_counts"]["test"] == 35, "Sealed Test metadata count mismatch"
    )
    require(
        release["document_counts"]["total"] == 429, "Dataset total metadata mismatch"
    )
    for document in [*train_docs, *val_docs]:
        previous_end = -1
        for entity in sorted(
            document.entities, key=lambda item: (item.start, item.end)
        ):
            require(
                document.raw_text[entity.start : entity.end] == entity.text,
                "Span text mismatch",
            )
            require(entity.start >= previous_end, "Overlapping entity spans")
            previous_end = entity.end

    expected_active = [entity_type.value for entity_type in DEFAULT_ACTIVE_ENTITY_TYPES]
    require(
        config["token_ner"]["active_entity_types"] == expected_active,
        "Active classes mismatch",
    )
    labels, _, _ = build_label_map(expected_active)
    require(
        len(labels) == config["token_ner"]["num_labels"] == 13,
        "BIO label count mismatch",
    )
    require(
        all(model["max_input_tokens"] == 256 for model in config["models"].values()),
        "Input policy mismatch",
    )
    require(
        config["hyperparameters"]["content_overlap"] == 64, "Content overlap mismatch"
    )
    require(protocol_path.is_file(), "Benchmark protocol is missing")
    protocol_text = protocol_path.read_text(encoding="utf-8")
    for contract_text in [
        "Shuffled Token-Window Batching with Single-Loss Ownership",
        "Protocol-B official runs",
        "prescription_macro_entity_f1",
        "The official evaluator has no `--force`",
        "max_input_tokens = 256",
    ]:
        require(
            contract_text in protocol_text,
            f"Protocol contract missing: {contract_text}",
        )
    for model in config["models"].values():
        require(
            len(model["backbone_revision"]) == 40,
            "Backbone revision is not pinned",
        )
        require(
            len(model["tokenizer_revision"]) == 40,
            "Tokenizer revision is not pinned",
        )
    for audit_script in [
        "audit_sampling.py",
        "audit_tokenizers.py",
        "audit_trainability_by_class.py",
        "verify_token_alignment_all_models.py",
    ]:
        audit_source = (root_dir / "scripts" / audit_script).read_text(encoding="utf-8")
        require(
            '["train", "val", "test"]' not in audit_source,
            f"Pre-training audit attempts to parse sealed Test: {audit_script}",
        )

    pytest_command = [sys.executable, "-m", "pytest", "tests/training/", "-q"]
    test_run = subprocess.run(
        pytest_command,
        cwd=root_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    require(
        test_run.returncode == 0,
        f"Training contract tests failed:\n{test_run.stdout}\n{test_run.stderr}",
    )

    return {
        "dataset_version": release["dataset_version"],
        "document_counts": release["document_counts"],
        "labels": len(labels),
        "test_output": test_run.stdout.strip(),
        "checks": [
            "Dataset integrity and release metadata",
            "6 active classes / 13 BIO labels",
            "Unified content-only tokenizer",
            "Per-window special tokens and total capacity",
            "100% gold-window enclosure for all three backbones",
            "Every token owns loss exactly once",
            "No broken BIO across overlap",
            "Global-token logit merge",
            "Document-aware entity evaluation",
            "Empty-gold exclusion and FP rates",
            "Active-class macro numerical contract",
            "Smoke and tuning Test access blocked",
            "Direct self-finalization impossible",
            "No evaluator force/test-file bypass",
            "One global LR across complete seed grid",
            "Official runs require selection manifest",
            "Protocol/config/code v1.2 synchronized",
        ],
    }


def main() -> None:
    print("=========================================")
    print("RXIE HARDENED PRE-TRAINING RELEASE GATE")
    print("=========================================")
    result = run_hardened_release_gate()
    for check in result["checks"]:
        print(f"{check:<55} PASS")
    print(result["test_output"])
    print("=========================================")
    print("READY FOR E0 BENCHMARK TRAINING: YES")
    print("=========================================")


if __name__ == "__main__":
    main()

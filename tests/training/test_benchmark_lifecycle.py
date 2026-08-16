"""Negative authorization and global selection tests for Protocol B."""

import json
from pathlib import Path

import pytest
import yaml

from rxie.benchmark_protocol import (
    BENCHMARK_IMPLEMENTATION_FILES,
    SELECTION_SCHEMA_VERSION,
    benchmark_implementation_sha256,
    payload_sha256,
    select_global_learning_rate,
    sha256_directory,
    sha256_file,
)
from scripts.evaluate_final_test import (
    authorize_official_checkpoint,
)
from scripts.evaluate_final_test import (
    build_argument_parser as evaluator_parser,
)
from scripts.train_token_ner import build_argument_parser as training_parser
from scripts.train_token_ner import run_training

SEEDS = [42, 3407, 2026]
LRS = [1e-5, 2e-5, 3e-5, 5e-5]


def _candidates():
    scores = {
        1e-5: [0.5, 0.5, 0.5],
        2e-5: [0.9, 0.4, 0.8],
        3e-5: [0.6, 0.7, 0.6],
        5e-5: [0.4, 0.9, 0.3],
    }
    return [
        {
            "seed": seed,
            "learning_rate": learning_rate,
            "primary_metric": scores[learning_rate][seed_index],
            "secondary_metric": 0.5 + seed_index / 100,
        }
        for learning_rate in LRS
        for seed_index, seed in enumerate(SEEDS)
    ]


def test_selector_uses_one_lr_aggregated_across_all_seeds():
    aggregates, selected_lr = select_global_learning_rate(
        _candidates(),
        seeds=SEEDS,
        learning_rates=LRS,
    )
    assert len(aggregates) == 4
    assert selected_lr == 2e-5
    assert all(len(row["seed_values"]) == 3 for row in aggregates)


def test_selector_rejects_incomplete_or_duplicate_grid():
    with pytest.raises(ValueError, match="Incomplete"):
        select_global_learning_rate(_candidates()[:-1], seeds=SEEDS, learning_rates=LRS)
    with pytest.raises(ValueError, match="Duplicate"):
        select_global_learning_rate(
            [*_candidates(), _candidates()[0]],
            seeds=SEEDS,
            learning_rates=LRS,
        )


def test_official_cli_has_no_direct_final_or_force_bypass():
    with pytest.raises(SystemExit):
        training_parser().parse_args(["--run-type", "final"])
    with pytest.raises(SystemExit):
        evaluator_parser().parse_args(["--checkpoint-dir", "x", "--force"])
    with pytest.raises(SystemExit):
        evaluator_parser().parse_args(["--checkpoint-dir", "x", "--test-file", "fake"])
    with pytest.raises(SystemExit):
        evaluator_parser().parse_args(["--checkpoint-dir", "x", "--config", "fake"])


@pytest.mark.parametrize(
    "arguments",
    [
        ["--run-type", "official", "--seed", "42"],
        [
            "--run-type",
            "tuning",
            "--seed",
            "42",
            "--learning-rate",
            "2e-5",
            "--epochs",
            "1",
        ],
    ],
)
def test_benchmark_modes_reject_missing_selection_or_hyperparameter_override(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
):
    monkeypatch.setattr("sys.argv", ["train_token_ner.py", *arguments])
    with pytest.raises(SystemExit):
        run_training()


def test_smoke_or_tuning_manifest_cannot_authorize_test(tmp_path: Path):
    config = {
        "protocol_version": "rxie.benchmark_protocol.v1.2.0",
        "dataset_version": "rxie-dataset-v1.0.1",
        "seeds": SEEDS,
        "models": {"E0_phobert": {}},
        "hyperparameters": {"learning_rates": LRS},
    }
    config_path = tmp_path / "configs" / "benchmark_v1.yaml"
    for relative_path in BENCHMARK_IMPLEMENTATION_FILES:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    for run_type in ["smoke", "tuning"]:
        with pytest.raises(PermissionError, match="official"):
            authorize_official_checkpoint(
                tmp_path / "checkpoint",
                {
                    "manifest_schema_version": "rxie.checkpoint_manifest.v2",
                    "run_type": run_type,
                },
                config=config,
                config_path=config_path,
                repository_root=tmp_path,
            )


def test_valid_official_cohort_requires_selector_manifest(tmp_path: Path):
    config = {
        "protocol_version": "rxie.benchmark_protocol.v1.2.0",
        "dataset_version": "rxie-dataset-v1.0.1",
        "seeds": SEEDS,
        "models": {
            "E0_phobert": {
                "backbone_id": "example/model",
                "backbone_revision": "a" * 40,
                "tokenizer_id": "example/model",
                "tokenizer_revision": "a" * 40,
                "max_input_tokens": 256,
            }
        },
        "token_ner": {
            "active_entity_types": [
                "DRUG",
                "STRENGTH",
                "DOSAGE",
                "FREQUENCY",
                "ROUTE",
                "INSTRUCTION",
            ],
            "num_labels": 13,
        },
        "hyperparameters": {
            "learning_rates": LRS,
            "content_overlap": 64,
            "batch_size": 8,
            "epochs_max": 20,
            "weight_decay": 0.01,
            "warmup_ratio": 0.1,
        },
        "sampling": {
            "policy": "shuffled_token_window_batching_with_single_loss_ownership"
        },
    }
    config_path = tmp_path / "configs" / "benchmark_v1.yaml"
    for relative_path in BENCHMARK_IMPLEMENTATION_FILES:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    implementation_hash = benchmark_implementation_sha256(tmp_path)
    source_commit = "b" * 40
    candidates = []
    for candidate in _candidates():
        run_dir = (
            tmp_path
            / "experiments"
            / "E0_phobert"
            / "tuning"
            / f"lr_{candidate['learning_rate']:.1e}_seed_{candidate['seed']}"
        )
        run_dir.mkdir(parents=True)
        metrics = {
            "prescription_macro_summary": {
                "prescription_macro_entity_f1": candidate["primary_metric"]
            },
            "entity_micro": {"f1": candidate["secondary_metric"]},
        }
        checkpoint_manifest = {
            "manifest_schema_version": "rxie.checkpoint_manifest.v2",
            "protocol_version": config["protocol_version"],
            "run_type": "tuning",
            "model_id": "E0_phobert",
            "seed": candidate["seed"],
            "learning_rate": candidate["learning_rate"],
            "dataset_version": config["dataset_version"],
            "config_sha256": sha256_file(config_path),
            "max_input_tokens": 256,
            "content_overlap": 64,
            "active_entity_types": config["token_ner"]["active_entity_types"],
            "num_labels": 13,
            "backbone_id": "example/model",
            "backbone_revision": "a" * 40,
            "tokenizer_id": "example/model",
            "tokenizer_revision": "a" * 40,
            "batch_size": 8,
            "epochs_max": 20,
            "weight_decay": 0.01,
            "warmup_ratio": 0.1,
            "sampling_policy": config["sampling"]["policy"],
            "benchmark_implementation_sha256": implementation_hash,
            "source_git_dirty": False,
            "source_git_commit": source_commit,
            "best_validation_metric": candidate["primary_metric"],
        }
        environment_path = run_dir / "environment.json"
        environment_path.write_text(
            json.dumps({"seed": candidate["seed"]}), encoding="utf-8"
        )
        checkpoint_manifest["environment_sha256"] = sha256_file(environment_path)
        manifest_path = run_dir / "checkpoint_manifest.json"
        metrics_path = run_dir / "metrics_val.json"
        manifest_path.write_text(json.dumps(checkpoint_manifest), encoding="utf-8")
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        candidates.append(
            {
                **candidate,
                "run_path": str(run_dir.relative_to(tmp_path)),
                "checkpoint_manifest_sha256": sha256_file(manifest_path),
                "metrics_val_sha256": sha256_file(metrics_path),
                "source_git_commit": source_commit,
            }
        )

    aggregates, selected_lr = select_global_learning_rate(
        candidates, seeds=SEEDS, learning_rates=LRS
    )
    selection = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "protocol_version": config["protocol_version"],
        "model_id": "E0_phobert",
        "dataset_version": config["dataset_version"],
        "config_sha256": sha256_file(config_path),
        "candidates": candidates,
        "aggregates": aggregates,
        "selected_lr": selected_lr,
    }
    selection["payload_sha256"] = payload_sha256(selection)
    selection_path = tmp_path / "reports" / "selection.json"
    selection_path.parent.mkdir(parents=True)
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    selection_hash = sha256_file(selection_path)

    release_dir = tmp_path / "data" / "ner_dataset"
    release_dir.mkdir(parents=True)
    release = {
        "dataset_version": config["dataset_version"],
        "file_checksums_sha256": {
            "train.jsonl": "1" * 64,
            "val.jsonl": "2" * 64,
            "test.jsonl": "3" * 64,
        },
    }
    (release_dir / "release_manifest.json").write_text(
        json.dumps(release), encoding="utf-8"
    )

    labels = ["O"]
    for entity_type in config["token_ner"]["active_entity_types"]:
        labels.extend([f"B-{entity_type}", f"I-{entity_type}"])

    manifests = {}
    for seed in SEEDS:
        run_dir = tmp_path / "experiments" / "E0_phobert" / "official" / f"seed_{seed}"
        run_dir.mkdir(parents=True)
        best_checkpoint = run_dir / "best_checkpoint"
        best_checkpoint.mkdir()
        (best_checkpoint / "weights.bin").write_bytes(b"weights")
        environment_path = run_dir / "environment.json"
        environment_path.write_text(json.dumps({"seed": seed}), encoding="utf-8")
        manifest = {
            "manifest_schema_version": "rxie.checkpoint_manifest.v2",
            "protocol_version": config["protocol_version"],
            "run_type": "official",
            "model_id": "E0_phobert",
            "seed": seed,
            "learning_rate": selected_lr,
            "selection_manifest_path": "reports/selection.json",
            "selection_manifest_sha256": selection_hash,
            "source_git_dirty": False,
            "source_git_commit": source_commit,
            "config_sha256": sha256_file(config_path),
            "dataset_version": config["dataset_version"],
            "dataset_checksums": {
                "train.jsonl": "1" * 64,
                "val.jsonl": "2" * 64,
                "test.jsonl": "3" * 64,
            },
            "max_input_tokens": 256,
            "content_overlap": 64,
            "active_entity_types": config["token_ner"]["active_entity_types"],
            "num_labels": 13,
            "labels": labels,
            "backbone_id": "example/model",
            "backbone_revision": "a" * 40,
            "tokenizer_id": "example/model",
            "tokenizer_revision": "a" * 40,
            "batch_size": 8,
            "epochs_max": 20,
            "weight_decay": 0.01,
            "warmup_ratio": 0.1,
            "sampling_policy": config["sampling"]["policy"],
            "benchmark_implementation_sha256": implementation_hash,
            "best_checkpoint_sha256": sha256_directory(best_checkpoint),
            "environment_sha256": sha256_file(environment_path),
        }
        (run_dir / "checkpoint_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        manifests[seed] = (run_dir, manifest)

    run_dir, manifest = manifests[42]
    authorized = authorize_official_checkpoint(
        run_dir,
        manifest,
        config=config,
        config_path=config_path,
        repository_root=tmp_path,
    )
    assert authorized["selected_lr"] == 2e-5

    critical_source = tmp_path / "scripts" / "train_token_ner.py"
    original_source = critical_source.read_text(encoding="utf-8")
    critical_source.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="benchmark_implementation_sha256"):
        authorize_official_checkpoint(
            run_dir,
            manifest,
            config=config,
            config_path=config_path,
            repository_root=tmp_path,
        )
    critical_source.write_text(original_source, encoding="utf-8")

    first_metrics = tmp_path / candidates[0]["run_path"] / "metrics_val.json"
    original_metrics = first_metrics.read_text(encoding="utf-8")
    first_metrics.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="metrics were modified"):
        authorize_official_checkpoint(
            run_dir,
            manifest,
            config=config,
            config_path=config_path,
            repository_root=tmp_path,
        )
    first_metrics.write_text(original_metrics, encoding="utf-8")

    wrong_seed_manifest = manifests[3407][1] | {"seed": 42}
    sibling_manifest_path = manifests[3407][0] / "checkpoint_manifest.json"
    sibling_manifest_path.write_text(json.dumps(wrong_seed_manifest), encoding="utf-8")
    with pytest.raises(PermissionError, match="cohort is inconsistent"):
        authorize_official_checkpoint(
            run_dir,
            manifest,
            config=config,
            config_path=config_path,
            repository_root=tmp_path,
        )
    sibling_manifest_path.write_text(json.dumps(manifests[3407][1]), encoding="utf-8")

    (manifests[3407][0] / "checkpoint_manifest.json").unlink()
    with pytest.raises(PermissionError, match="three official seeds"):
        authorize_official_checkpoint(
            run_dir,
            manifest,
            config=config,
            config_path=config_path,
            repository_root=tmp_path,
        )

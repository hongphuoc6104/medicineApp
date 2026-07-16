"""Fake-only tests for WP-01 preflight and privacy-safe reporting."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import wp01_baseline_tooling as tooling
from scripts import wp01_baseline_worker as worker


PINNED = "a6810a392c97593f073a9c5e2b8dfc47027c1911"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project = tmp_path / "project"
    assets = tmp_path / "assets"
    project.mkdir()
    assets.mkdir()
    scripts_dir = project / "scripts"
    scripts_dir.mkdir()
    worker = scripts_dir / "wp01_baseline_worker.py"
    worker.write_text("# fake worker\n", encoding="utf-8")
    model = assets / "model.bin"
    model.write_bytes(b"fake model")
    image = assets / "record.bin"
    image.write_bytes(b"fake private input")
    manifest = project / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["image_id", "split", "relative_path", "sha256", "include_eval"])
        writer.writeheader()
        writer.writerow(
            {
                "image_id": "opaque-1",
                "split": "core_labeled",
                "relative_path": "record.bin",
                "sha256": _hash(image),
                "include_eval": "yes",
            }
        )
    requirements = project / "requirements.json"
    _write_json(
        requirements,
        {
            "baseline_commit": PINNED,
            "input_manifest": {
                "id": "manifest",
                "relative_path": str(manifest.relative_to(tooling.ROOT)) if manifest.is_relative_to(tooling.ROOT) else "unused",
                "sha256": _hash(manifest),
                "included_rows": 1,
                "split_counts": {"core_labeled": 1},
            },
            "tracked_evaluator_assets": [],
            "runtime_assets": [
                {
                    "id": "model",
                    "role": "model",
                    "relative_path": "model.bin",
                    "kind": "file",
                    "sha256": _hash(model),
                }
            ],
            "benchmark_policy": {"seed": 42, "thread_count": 1, "warm_repetitions_per_image": 3, "debug_level": "metadata"},
        },
    )
    approval = project / "approval.json"
    decision = {
        "approved": True,
        "approved_by": "reviewer",
        "recorded_at": "2026-07-16T00:00:00Z",
        "reference": "decision-1",
    }
    _write_json(
        approval,
        {
            "baseline_execution": {
                **decision,
                "baseline_commit": PINNED,
                "manifest_sha256": _hash(manifest),
                "image_count": 1,
                "labeled_count": 1,
                "operational_count": 0,
            },
            "privacy_approval": {
                **decision,
                "manifest_sha256": _hash(manifest),
                "image_count": 1,
                "labeled_count": 1,
                "operational_count": 0,
                "allowed_purpose": "WP-01 baseline evaluation",
            },
            "debug_retention": {
                **decision,
                "delete_after": (date.today() + timedelta(days=30)).isoformat(),
                "local_directory_only": True,
            },
        },
    )
    return requirements, approval, assets, manifest


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **changes) -> dict:
    requirements, approval, assets, manifest = _fixture(tmp_path)
    payload = json.loads(requirements.read_text(encoding="utf-8"))
    # Tracked files normally live below ROOT; redirect that one resolver in fake tests.
    monkeypatch.setattr(tooling, "ROOT", manifest.parent)
    payload["input_manifest"]["relative_path"] = manifest.name
    if "requirements" in changes:
        changes.pop("requirements")(payload)
    _write_json(requirements, payload)
    if "approval" in changes:
        approval_payload = json.loads(approval.read_text(encoding="utf-8"))
        changes.pop("approval")(approval_payload)
        _write_json(approval, approval_payload)
    roots = changes.pop("asset_roots", [assets])
    return tooling.run_preflight(
        requirements,
        approval,
        tmp_path,
        roots,
        changes.pop("device", "cpu"),
        commit_resolver=changes.pop("commit_resolver", lambda _: (PINNED, False)),
    )


def test_preflight_passes_fakes_without_importing_model_packages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = {name for name in sys.modules if name.startswith(tooling.MODEL_IMPORT_PREFIXES)}
    result = _run(tmp_path, monkeypatch)
    after = {name for name in sys.modules if name.startswith(tooling.MODEL_IMPORT_PREFIXES)}

    assert result["passed"] is True
    assert result["worker_sha256"] == _hash(tooling.ROOT / "scripts" / "wp01_baseline_worker.py")
    assert after == before


def test_worker_hash_is_part_of_gate_fingerprint() -> None:
    base = {
        "baseline_commit": PINNED,
        "code_state": {"tree_digest": "1" * 40},
        "requirements_sha256": "2" * 64,
        "approval_sha256": "3" * 64,
        "evaluator_sha256": "4" * 64,
        "worker_sha256": "5" * 64,
        "input_content_sha256": "6" * 64,
        "tracked_inventory": [],
        "runtime_inventory": [],
        "benchmark_policy": {},
        "process_config": {},
    }

    assert tooling.gate_fingerprint(base) != tooling.gate_fingerprint(
        {**base, "worker_sha256": "7" * 64}
    )


@pytest.mark.parametrize(
    ("change_key", "change", "expected"),
    [
        ("approval", lambda value: value["baseline_execution"].update(approved=False), "approval:baseline_execution:not_approved"),
        ("approval", lambda value: value["privacy_approval"].update(approved=False), "approval:privacy_approval:not_approved"),
        (
            "approval",
            lambda value: value["privacy_approval"].update(manifest_sha256="0" * 64),
            "approval:privacy_approval:manifest_mismatch",
        ),
        (
            "approval",
            lambda value: value["baseline_execution"].update(labeled_count=0),
            "approval:baseline_execution:split_counts_mismatch",
        ),
        ("approval", lambda value: value["debug_retention"].update(delete_after=""), "approval:debug_retention:missing_or_invalid_deadline"),
        ("requirements", lambda value: value["runtime_assets"][0].update(sha256=""), "hash:model:missing"),
    ],
)
def test_preflight_refuses_missing_decisions_or_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change_key: str,
    change,
    expected: str,
) -> None:
    result = _run(tmp_path, monkeypatch, **{change_key: change})
    assert result["passed"] is False
    assert expected in result["errors"]


def test_preflight_refuses_missing_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run(tmp_path, monkeypatch, asset_roots=[])
    assert result["passed"] is False
    assert "asset:model:missing_or_symlink" in result["errors"]


def test_read_only_locator_refuses_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target.bin"
    target.write_bytes(b"asset")
    (root / "model.bin").symlink_to(target)
    with pytest.raises(FileNotFoundError):
        tooling.locate_asset({"id": "model", "relative_path": "model.bin", "kind": "file"}, [root])


def test_cpu_and_gpu_run_identity_and_process_config_are_distinct() -> None:
    cpu = tooling.build_process_config("cpu", 1)
    gpu = tooling.build_process_config("gpu", 1)
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)

    assert cpu != gpu
    assert tooling.make_run_id("cpu", cpu, now) != tooling.make_run_id("gpu", gpu, now)
    assert cpu["cuda_enabled"] is False
    assert gpu["cuda_enabled"] is True
    assert cpu["environment"]["CUDA_VISIBLE_DEVICES"] == "-1"
    assert cpu["environment"]["NVIDIA_VISIBLE_DEVICES"] == "none"
    assert cpu["environment"]["PADDLE_DEVICE"] == "cpu"
    assert "paddle_cuda_capability_masked" in cpu["enforcement"]
    assert gpu["environment"]["CUDA_VISIBLE_DEVICES"] == "0"


def test_runtime_binding_contract_requires_every_hashed_asset() -> None:
    asset_ids = {
        "yolo_prescription",
        "phobert_ner",
        "vietocr_vgg_transformer",
        "paddle_text_detection",
        "paddle_loaded_recognizer",
        "paddle_document_orientation",
        "drug_database",
    }
    bindings = {asset_id: f"explicit:{asset_id}" for asset_id in asset_ids}

    tooling.validate_runtime_bindings(asset_ids, bindings)
    bindings.pop("paddle_loaded_recognizer")
    with pytest.raises(tooling.PreflightFailure, match="paddle_loaded_recognizer"):
        tooling.validate_runtime_bindings(asset_ids, bindings)


def test_fresh_preflight_must_match_receipt_gate_fingerprint() -> None:
    receipt = {"passed": True, "gate_fingerprint": "a" * 64}
    fresh = {"passed": True, "gate_fingerprint": "b" * 64}

    with pytest.raises(tooling.PreflightFailure, match="fresh preflight"):
        tooling.validate_fresh_preflight(receipt, fresh)
    tooling.validate_fresh_preflight(receipt, {**fresh, "gate_fingerprint": "a" * 64})


def test_code_state_rejects_dirty_or_shadowing_untracked_modules() -> None:
    clean = {
        "commit": PINNED,
        "tree_digest": "1" * 40,
        "tracked_dirty": False,
        "prohibited_untracked": [],
    }
    assert tooling.validate_code_state(clean, PINNED, "1" * 40) == []
    dirty = {**clean, "tracked_dirty": True}
    shadowed = {**clean, "prohibited_untracked": ["core.py", "core/evil.py"]}
    changed_tree = {**clean, "tree_digest": "2" * 40}

    assert "code:tracked_worktree_dirty" in tooling.validate_code_state(dirty, PINNED, "1" * 40)
    assert "code:prohibited_untracked_module_shadow" in tooling.validate_code_state(shadowed, PINNED, "1" * 40)
    assert "code:source_tree_digest_mismatch" in tooling.validate_code_state(changed_tree, PINNED, "1" * 40)


def test_result_contract_rejects_missing_extra_duplicate_and_wrong_repetition() -> None:
    expected = [
        {"image_id": "a", "split": "core_labeled"},
        {"image_id": "b", "split": "extended_unlabeled"},
    ]
    valid = [
        {"image_id": image_id, "split": split, "repetition": repetition}
        for repetition in (1, 2)
        for image_id, split in (("a", "core_labeled"), ("b", "extended_unlabeled"))
    ]
    tooling.validate_result_records(valid, expected, 2)

    for invalid in (
        valid[:-1],
        valid + [{"image_id": "extra", "split": "extended_unlabeled", "repetition": 1}],
        valid + [deepcopy(valid[0])],
        [{**row, "repetition": 3} if row is valid[0] else row for row in valid],
    ):
        with pytest.raises(ValueError, match="result contract"):
            tooling.validate_result_records(invalid, expected, 2)


def test_observation_contract_requires_stage_timings_and_resources() -> None:
    record = {
        "stage_timings_s": {stage: 0.1 for stage in tooling.REQUIRED_TIMING_STAGES},
        "resource_usage": {field: 1.0 for field in tooling.REQUIRED_RESOURCE_FIELDS},
    }
    cold = {
        "stage_timings_s": dict(record["stage_timings_s"]),
        "initialization_timings_s": {
            stage: 0.2 for stage in tooling.REQUIRED_INITIALIZATION_STAGES
        },
        "cold_total_s": 2.0,
        "resource_usage": dict(record["resource_usage"]),
    }
    tooling.validate_observation_metrics([record], cold)

    for invalid_record, invalid_cold in (
        ({**record, "stage_timings_s": {}}, cold),
        ({**record, "resource_usage": {}}, cold),
        (record, {**cold, "stage_timings_s": {}}),
        (record, {**cold, "initialization_timings_s": {}}),
        (record, {**cold, "cold_total_s": None}),
        (record, {**cold, "resource_usage": {}}),
    ):
        with pytest.raises(ValueError, match="timing/resource contract"):
            tooling.validate_observation_metrics([invalid_record], invalid_cold)


def test_cold_scope_wraps_initialization_and_first_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    events = []
    real_snapshot = worker.resource_snapshot

    def snapshot():
        events.append("resource_snapshot")
        return real_snapshot()

    monkeypatch.setattr(worker, "resource_snapshot", snapshot)

    def initialize():
        events.append("construct_models")
        timings = {stage: 0.0 for stage in worker.REQUIRED_INITIALIZATION_STAGES}
        return "runtime", timings

    def first_inference(runtime):
        assert runtime == "runtime"
        events.append("first_inference")
        return {"ok": True}, {stage: 0.0 for stage in worker.REQUIRED_TIMING_STAGES}

    runtime, result, cold = worker.measure_cold_observation(initialize, first_inference)

    assert runtime == "runtime"
    assert result == {"ok": True}
    assert events == [
        "resource_snapshot",
        "construct_models",
        "first_inference",
        "resource_snapshot",
    ]
    assert cold["cold_total_s"] >= cold["initialization_timings_s"]["initialization_total"]
    assert set(cold["initialization_timings_s"]) == set(worker.REQUIRED_INITIALIZATION_STAGES)


def test_expired_private_run_cleanup_is_confined_and_enforced(tmp_path: Path) -> None:
    local_root = tmp_path / "local" / "wp01"
    expired = local_root / "runs" / "expired"
    active = local_root / "runs" / "active"
    expired.mkdir(parents=True)
    active.mkdir(parents=True)
    (expired / "private_results.jsonl").write_text("private", encoding="utf-8")
    (active / "private_results.jsonl").write_text("private", encoding="utf-8")
    _write_json(expired / "retention.json", {"delete_after": "2020-01-01"})
    _write_json(active / "retention.json", {"delete_after": "2099-01-01"})

    removed = tooling.cleanup_expired_private_artifacts(local_root, today=date(2026, 7, 16))

    assert removed == ["runs/expired"]
    assert not expired.exists()
    assert active.exists()


def test_report_separates_correctness_and_operational_metrics_without_sensitive_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    eval_dir = root / "data" / "eval"
    run_dir = root / "local" / "wp01" / "runs" / "fake-run"
    eval_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    labeled_ids = [f"private-labeled-{index}" for index in range(50)]
    operational_ids = [f"private-operational-{index}" for index in range(120)]
    gt_path = eval_dir / "gt_drugs_by_image.json"
    alias_path = eval_dir / "canonical_drug_aliases.json"
    worker_path = root / "scripts" / "wp01_baseline_worker.py"
    worker_path.parent.mkdir()
    worker_path.write_text("# worker\n", encoding="utf-8")
    _write_json(
        gt_path,
        {
            "images": [
                {"image_id": image_id, "expected_drugs": [{"canonical_id": "known"}]}
                for image_id in labeled_ids
            ]
        },
    )
    _write_json(
        alias_path,
        {"canonical_drugs": [{"canonical_id": "known", "aliases": ["known drug"]}]},
    )
    receipt = {
        "run_id": "approved-main-a6810a3-cpu-fake",
        "baseline_commit": PINNED,
        "requirements_sha256": "1" * 64,
        "evaluator_sha256": _hash(Path(tooling.__file__)),
        "worker_sha256": _hash(worker_path),
        "input_content_sha256": "3" * 64,
        "tracked_inventory": [
            {"id": "phase_a_eval_v2_170", "sha256": "4" * 64},
            {"id": "ground_truth_50", "sha256": _hash(gt_path)},
            {"id": "canonical_aliases", "sha256": _hash(alias_path)},
        ],
        "runtime_inventory": [{"id": "fake_model", "role": "model", "sha256": "5" * 64}],
        "benchmark_policy": {"seed": 42, "warm_repetitions_per_image": 1, "debug_level": "metadata"},
        "process_config": {
            "device": "cpu",
            "threads": 1,
            "cuda_enabled": False,
            "enforcement": ["paddle_cuda_capability_masked"],
            "environment": {"CUDA_VISIBLE_DEVICES": "-1"},
        },
        "environment": {"os": "TestOS"},
        "approval": {
            "privacy_approval": {"reference": "privacy-decision"},
            "debug_retention": {"delete_after": "2099-01-01"},
        },
        "input_rows": [
            *({"image_id": image_id, "split": "core_labeled"} for image_id in labeled_ids),
            *({"image_id": image_id, "split": "extended_unlabeled"} for image_id in operational_ids),
        ],
        "gate_fingerprint": "6" * 64,
        "code_state": {"tree_digest": "7" * 40},
    }
    _write_json(run_dir / "preflight_receipt.json", receipt)
    _write_json(run_dir / "retention.json", {"delete_after": "2099-01-01"})
    _write_json(
        run_dir / "runtime_metadata.json",
        {
            "gate_fingerprint": "6" * 64,
            "source_tree_digest": "7" * 40,
            "worker_sha256": _hash(worker_path),
            "cold_total_s": 5.0,
            "cold_observation": {
                "stage_timings_s": {stage: 0.2 for stage in tooling.REQUIRED_TIMING_STAGES},
                "initialization_timings_s": {
                    stage: 0.3 for stage in tooling.REQUIRED_INITIALIZATION_STAGES
                },
                "cold_total_s": 5.0,
                "resource_usage": {field: 2.0 for field in tooling.REQUIRED_RESOURCE_FIELDS},
            },
            "runtime_bindings": {"fake_model": "explicit:fake_model"},
        },
    )
    records = [
        *(
            {
                "image_id": image_id,
                "split": "core_labeled",
                "repetition": 1,
                "elapsed_s": 0.5,
                "stage_timings_s": {stage: 0.1 for stage in tooling.REQUIRED_TIMING_STAGES},
                "resource_usage": {field: 1.0 for field in tooling.REQUIRED_RESOURCE_FIELDS},
                "result": {"medications": [{"ocr_text": "KNOWN DRUG sensitive text"}]},
            }
            for image_id in labeled_ids
        ),
        *(
            {
                "image_id": image_id,
                "split": "extended_unlabeled",
                "repetition": 1,
                "elapsed_s": 0.7,
                "stage_timings_s": {stage: 0.1 for stage in tooling.REQUIRED_TIMING_STAGES},
                "resource_usage": {field: 1.0 for field in tooling.REQUIRED_RESOURCE_FIELDS},
                "result": {"medications": [], "error": "OCR found no text at /private/input.jpg"},
            }
            for image_id in operational_ids
        ),
    ]
    (run_dir / "private_results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(tooling, "ROOT", root)

    report = tooling.build_aggregate_report(run_dir)
    serialized = json.dumps(report)

    assert report["correctness_labeled_50"]["tp"] == 50
    assert report["correctness_labeled_50"]["macro_f1"] == 1.0
    assert report["operational_unlabeled_120"]["error_count"] == 120
    assert report["operational_unlabeled_120"]["empty_count"] == 120
    assert report["stage_timings"]["paddle_detection"]["warm"]["p95_s"] == 0.1
    assert report["cold_start"]["scope"] == "model_initialization_plus_first_inference"
    assert report["initialization_timings"]["phobert_initialization"]["p50_s"] == 0.3
    assert report["resource_usage"]["warm"]["sample_count"] == 170
    assert any(item["id"] == "wp01_baseline_worker" for item in report["provenance"]["evaluator_assets"])
    assert "sensitive text" not in serialized
    assert "private-labeled-0" not in serialized
    assert "/private/input.jpg" not in serialized


def test_report_rejects_tampered_evaluator_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    eval_dir = root / "data" / "eval"
    run_dir = root / "run"
    eval_dir.mkdir(parents=True)
    run_dir.mkdir()
    gt_path = eval_dir / "gt_drugs_by_image.json"
    alias_path = eval_dir / "canonical_drug_aliases.json"
    _write_json(gt_path, {"images": []})
    _write_json(alias_path, {"canonical_drugs": []})
    _write_json(
        run_dir / "preflight_receipt.json",
        {
            "tracked_inventory": [
                {"id": "ground_truth_50", "sha256": _hash(gt_path)},
                {"id": "canonical_aliases", "sha256": "0" * 64},
            ],
            "approval": {"debug_retention": {"delete_after": "2099-01-01"}},
        },
    )
    _write_json(run_dir / "retention.json", {"delete_after": "2099-01-01"})
    (run_dir / "private_results.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(tooling, "ROOT", root)

    with pytest.raises(ValueError, match="canonical_aliases"):
        tooling.build_aggregate_report(run_dir)

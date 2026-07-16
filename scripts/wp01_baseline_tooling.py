#!/usr/bin/env python3
"""Approval-gated WP-01 baseline preflight, runner, and safe report builder.

Preflight uses only the Python standard library. Model/OCR imports are deferred to
``wp01_baseline_worker.py`` and that worker requires a passing local receipt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUIREMENTS = ROOT / "config" / "wp01_asset_requirements.json"
DEFAULT_APPROVAL = ROOT / "local" / "wp01" / "approval.json"
LOCAL_ROOT = ROOT / "local" / "wp01"
REPORT_ROOT = ROOT / "reports" / "wp01"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MODEL_IMPORT_PREFIXES = (
    "cv2",
    "numpy",
    "paddle",
    "paddleocr",
    "torch",
    "transformers",
    "ultralytics",
    "vietocr",
)
REQUIRED_TIMING_STAGES = (
    "yolo",
    "deskew",
    "orientation",
    "paddle_detection",
    "vietocr_recognition",
    "layout_grouping",
    "phobert_ner",
    "drug_lookup",
    "total",
)
REQUIRED_INITIALIZATION_STAGES = (
    "model_framework_imports",
    "yolo_initialization",
    "paddle_detection_recognition_initialization",
    "vietocr_initialization",
    "orientation_initialization",
    "phobert_initialization",
    "drug_lookup_initialization",
    "initialization_total",
)
REQUIRED_RESOURCE_FIELDS = (
    "process_cpu_s",
    "user_cpu_s",
    "system_cpu_s",
    "max_rss_kb",
    "voluntary_context_switches",
    "involuntary_context_switches",
)


class PreflightFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path, relative_files: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(relative_files):
        path = root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _safe_relative_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or not raw or ".." in path.parts:
        raise ValueError(f"Asset path must be a safe relative path: {raw!r}")
    return path


def _contains_symlink(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def locate_asset(spec: dict, roots: list[Path]) -> tuple[Path, Path]:
    """Locate an asset without creating, copying, linking, or opening it writable."""
    relative = _safe_relative_path(spec.get("relative_path", ""))
    for raw_root in roots:
        if raw_root.expanduser().is_symlink():
            continue
        root = raw_root.expanduser().resolve()
        candidate = root / relative
        if _contains_symlink(root, relative):
            continue
        kind = spec.get("kind", "file")
        if kind == "file" and candidate.is_file():
            return candidate, root
        if kind == "tree" and candidate.is_dir():
            files = spec.get("files") or []
            if files and all(
                (candidate / _safe_relative_path(item)).is_file()
                and not _contains_symlink(candidate, _safe_relative_path(item))
                for item in files
            ):
                return candidate, root
    raise FileNotFoundError(spec.get("id", spec.get("relative_path", "unknown")))


def observed_asset_hash(spec: dict, path: Path) -> str:
    if spec.get("kind", "file") == "tree":
        return sha256_tree(path, spec.get("files") or [])
    return sha256_file(path)


def default_commit_resolver(code_root: Path) -> dict:
    commit = subprocess.run(
        ["git", "-C", str(code_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree_digest = subprocess.run(
        ["git", "-C", str(code_root), "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status_output = subprocess.run(
        ["git", "-C", str(code_root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8", errors="surrogateescape")
    status_entries = [entry for entry in status_output.split("\0") if entry]
    tracked_dirty = any(not entry.startswith("?? ") for entry in status_entries)
    prohibited_suffixes = (".py", ".pyc", ".pyo", ".so", ".pyd")
    prohibited_untracked = set()
    for entry in status_entries:
        if not entry.startswith("?? "):
            continue
        relative = entry[3:]
        if relative.endswith(prohibited_suffixes) or "__pycache__" in Path(relative).parts:
            prohibited_untracked.add(relative)

    tracked_output = subprocess.run(
        ["git", "-C", str(code_root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8", errors="surrogateescape")
    tracked_paths = {path for path in tracked_output.split("\0") if path}
    candidates = []
    for child in code_root.iterdir():
        if child.is_file() and child.suffix.lower() in prohibited_suffixes:
            candidates.append(child)
        elif child.is_dir() and child.name != ".git":
            init_file = child / "__init__.py"
            if init_file.is_file():
                candidates.append(init_file)
    core_root = code_root / "core"
    if core_root.is_dir():
        candidates.extend(
            path
            for path in core_root.rglob("*")
            if path.is_file()
            and (path.suffix.lower() in prohibited_suffixes or "__pycache__" in path.parts)
        )
    for candidate in candidates:
        relative = candidate.relative_to(code_root).as_posix()
        if relative not in tracked_paths:
            prohibited_untracked.add(relative)
    return {
        "commit": commit,
        "tree_digest": tree_digest,
        "tracked_dirty": tracked_dirty,
        "prohibited_untracked": sorted(prohibited_untracked),
    }


def validate_code_state(state: dict, expected_commit: str, expected_tree: str | None) -> list[str]:
    errors = []
    if state.get("commit") != expected_commit:
        errors.append("code:baseline_commit_mismatch")
    if expected_tree and state.get("tree_digest") != expected_tree:
        errors.append("code:source_tree_digest_mismatch")
    if state.get("tracked_dirty"):
        errors.append("code:tracked_worktree_dirty")
    if state.get("prohibited_untracked"):
        errors.append("code:prohibited_untracked_module_shadow")
    return errors


def validate_runtime_bindings(expected_asset_ids: Iterable[str], bindings: dict) -> None:
    expected = set(expected_asset_ids)
    actual = set(bindings)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra or any(not str(bindings[key]).startswith("explicit:") for key in actual):
        raise PreflightFailure(
            f"Runtime asset binding mismatch; missing={missing}, extra={extra}"
        )


def _gate_payload(preflight: dict) -> dict:
    return {
        "baseline_commit": preflight["baseline_commit"],
        "source_tree_digest": preflight["code_state"]["tree_digest"],
        "requirements_sha256": preflight["requirements_sha256"],
        "approval_sha256": preflight["approval_sha256"],
        "evaluator_sha256": preflight["evaluator_sha256"],
        "worker_sha256": preflight["worker_sha256"],
        "input_content_sha256": preflight["input_content_sha256"],
        "tracked_inventory": preflight["tracked_inventory"],
        "runtime_inventory": preflight["runtime_inventory"],
        "benchmark_policy": preflight["benchmark_policy"],
        "process_config": preflight["process_config"],
    }


def gate_fingerprint(preflight: dict) -> str:
    encoded = json.dumps(_gate_payload(preflight), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_fresh_preflight(receipt: dict, fresh: dict) -> None:
    if not fresh.get("passed"):
        raise PreflightFailure("Worker fresh preflight did not pass")
    if receipt.get("gate_fingerprint") != fresh.get("gate_fingerprint"):
        raise PreflightFailure("Worker fresh preflight does not match receipt")


def build_process_config(device: str, threads: int) -> dict:
    if device not in {"cpu", "gpu"}:
        raise ValueError(f"Unsupported device: {device}")
    env = {
        "OMP_NUM_THREADS": str(threads),
        "MKL_NUM_THREADS": str(threads),
        "OPENBLAS_NUM_THREADS": str(threads),
        "NUMEXPR_NUM_THREADS": str(threads),
        "PYTHONHASHSEED": "42",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if device == "cpu":
        env.update(
            {
                "CUDA_VISIBLE_DEVICES": "-1",
                "NVIDIA_VISIBLE_DEVICES": "none",
                "FLAGS_selected_gpus": "",
                "PADDLE_DEVICE": "cpu",
            }
        )
        enforcement = [
            "cuda_visibility_disabled",
            "torch_cuda_must_be_unavailable",
            "paddle_device_forced_cpu",
            "paddle_cuda_capability_masked",
        ]
    else:
        env.update(
            {
                "CUDA_VISIBLE_DEVICES": "0",
                "NVIDIA_VISIBLE_DEVICES": "0",
                "FLAGS_selected_gpus": "0",
                "PADDLE_DEVICE": "gpu",
            }
        )
        enforcement = ["cuda_device_0_visible", "torch_cuda_required", "paddle_cuda_required"]
    return {
        "device": device,
        "threads": threads,
        "cuda_enabled": device == "gpu",
        "enforcement": enforcement,
        "environment": env,
    }


def make_run_id(device: str, process_config: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    config_hash = hashlib.sha256(
        json.dumps(process_config, sort_keys=True).encode("utf-8")
    ).hexdigest()[:8]
    return f"approved-main-a6810a3-{device}-{now:%Y%m%dT%H%M%SZ}-{config_hash}"


def _validate_approval(
    payload: dict,
    baseline_commit: str,
    manifest_sha256: str,
    image_count: int,
    split_counts: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    execution = payload.get("baseline_execution") or {}
    privacy = payload.get("privacy_approval") or {}
    retention = payload.get("debug_retention") or {}
    for name, decision in (
        ("baseline_execution", execution),
        ("privacy_approval", privacy),
        ("debug_retention", retention),
    ):
        if not decision:
            errors.append(f"approval:{name}:not_recorded")
            continue
        if decision.get("approved") is not True:
            errors.append(f"approval:{name}:not_approved")
        for field in ("approved_by", "recorded_at", "reference"):
            if not str(decision.get(field, "")).strip():
                errors.append(f"approval:{name}:missing_{field}")
        if decision.get("recorded_at"):
            recorded_at = str(decision["recorded_at"]).replace("Z", "+00:00")
            try:
                if datetime.fromisoformat(recorded_at).tzinfo is None:
                    errors.append(f"approval:{name}:recorded_at_missing_timezone")
            except ValueError:
                errors.append(f"approval:{name}:recorded_at_invalid")
    if execution and execution.get("baseline_commit") != baseline_commit:
        errors.append("approval:baseline_execution:commit_mismatch")
    for name, decision in (("baseline_execution", execution), ("privacy_approval", privacy)):
        if not decision:
            continue
        if decision.get("manifest_sha256") != manifest_sha256:
            errors.append(f"approval:{name}:manifest_mismatch")
        if decision.get("image_count") != image_count:
            errors.append(f"approval:{name}:image_count_mismatch")
        if (
            decision.get("labeled_count") != split_counts.get("core_labeled", 0)
            or decision.get("operational_count") != split_counts.get("extended_unlabeled", 0)
        ):
            errors.append(f"approval:{name}:split_counts_mismatch")
    if privacy and privacy.get("allowed_purpose") != "WP-01 baseline evaluation":
        errors.append("approval:privacy_approval:purpose_mismatch")
    if retention and retention.get("local_directory_only") is not True:
        errors.append("approval:debug_retention:not_local_only")
    if retention:
        try:
            delete_after = date.fromisoformat(str(retention.get("delete_after", "")))
            if delete_after <= date.today():
                errors.append("approval:debug_retention:deadline_not_future")
        except ValueError:
            errors.append("approval:debug_retention:missing_or_invalid_deadline")
    return errors


def _environment_metadata(device: str) -> dict:
    distributions = {}
    for name in (
        "opencv-python",
        "paddleocr",
        "paddlepaddle",
        "paddlepaddle-gpu",
        "torch",
        "transformers",
        "ultralytics",
        "vietocr",
    ):
        try:
            distributions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            distributions[name] = "not-installed"
    cpu_model = platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if not cpu_model and cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                cpu_model = line.split(":", 1)[1].strip()
                break
    try:
        ram_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        ram_bytes = None
    accelerator = {"requested": device}
    if device == "gpu":
        try:
            gpu = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip().splitlines()
            accelerator["nvidia_smi"] = gpu
        except (OSError, subprocess.SubprocessError):
            accelerator["nvidia_smi"] = []
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu_model": cpu_model or "unknown",
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": ram_bytes,
        "accelerator": accelerator,
        "distributions": distributions,
    }


def _validate_tracked_asset(spec: dict, errors: list[str]) -> dict | None:
    asset_id = spec.get("id", "unknown")
    expected = str(spec.get("sha256", ""))
    if not HASH_RE.fullmatch(expected) or expected == "0" * 64:
        errors.append(f"hash:{asset_id}:missing")
        return None
    try:
        path = ROOT / _safe_relative_path(spec.get("relative_path", ""))
    except ValueError:
        errors.append(f"asset:{asset_id}:invalid_relative_path")
        return None
    if not path.is_file() or path.is_symlink():
        errors.append(f"asset:{asset_id}:missing_or_symlink")
        return None
    observed = sha256_file(path)
    if observed != expected:
        errors.append(f"hash:{asset_id}:mismatch")
        return None
    return {"id": asset_id, "sha256": observed}


def _load_input_rows(manifest_path: Path, roots: list[Path], errors: list[str]) -> list[dict]:
    rows: list[dict] = []
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("include_eval", "").strip().lower() != "yes":
                continue
            row_id = row.get("image_id", "")
            expected = row.get("sha256", "")
            if not HASH_RE.fullmatch(expected):
                errors.append(f"hash:input:{row_id or 'unknown'}:missing")
                continue
            spec = {
                "id": f"input:{row_id}",
                "relative_path": row.get("relative_path", ""),
                "kind": "file",
            }
            try:
                path, _ = locate_asset(spec, roots)
            except (FileNotFoundError, ValueError):
                errors.append(f"asset:input:{row_id or 'unknown'}:missing_or_symlink")
                continue
            if sha256_file(path) != expected:
                errors.append(f"hash:input:{row_id}:mismatch")
                continue
            record_id = hashlib.sha256(
                "\0".join(
                    (
                        row.get("split", ""),
                        row_id,
                        row.get("relative_path", ""),
                        expected,
                    )
                ).encode("utf-8")
            ).hexdigest()
            rows.append(
                {
                    "record_id": record_id,
                    "image_id": row_id,
                    "split": row.get("split", ""),
                    "path": str(path),
                    "sha256": expected,
                }
            )
    return rows


def run_preflight(
    requirements_path: Path,
    approval_path: Path,
    code_root: Path,
    asset_roots: list[Path],
    device: str,
    *,
    commit_resolver: Callable[[Path], dict | tuple[str, bool]] = default_commit_resolver,
) -> dict:
    """Run all gates without importing OCR, numerical, or model packages."""
    errors: list[str] = []
    requirements = load_json(requirements_path)
    baseline_commit = requirements.get("baseline_commit", "")
    baseline_tree = requirements.get("baseline_source_tree_digest")
    manifest_spec = requirements.get("input_manifest") or {}
    image_count = int(manifest_spec.get("included_rows", 0))
    try:
        approval = load_json(approval_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        approval = {}
        errors.append("approval:file:missing_or_invalid")
    errors.extend(
        _validate_approval(
            approval,
            baseline_commit,
            str(manifest_spec.get("sha256", "")),
            image_count,
            manifest_spec.get("split_counts") or {},
        )
    )

    try:
        resolved_state = commit_resolver(code_root)
        if isinstance(resolved_state, tuple):
            actual_commit, dirty = resolved_state
            code_state = {
                "commit": actual_commit,
                "tree_digest": baseline_tree,
                "tracked_dirty": dirty,
                "prohibited_untracked": [],
            }
        else:
            code_state = resolved_state
            actual_commit = code_state.get("commit", "unavailable")
            dirty = bool(code_state.get("tracked_dirty"))
        errors.extend(validate_code_state(code_state, baseline_commit, baseline_tree))
    except (OSError, subprocess.SubprocessError):
        actual_commit = "unavailable"
        dirty = True
        code_state = {
            "commit": actual_commit,
            "tree_digest": "unavailable",
            "tracked_dirty": True,
            "prohibited_untracked": [],
        }
        errors.append("code:not_a_readable_git_worktree")

    tracked_inventory: list[dict] = []
    for spec in [manifest_spec, *(requirements.get("tracked_evaluator_assets") or [])]:
        item = _validate_tracked_asset(spec, errors)
        if item:
            tracked_inventory.append(item)

    runtime_inventory: list[dict] = []
    resolved_assets: dict[str, str] = {}
    resolved_roots: dict[str, str] = {}
    for spec in requirements.get("runtime_assets") or []:
        asset_id = spec.get("id", "unknown")
        expected = str(spec.get("sha256", ""))
        if not HASH_RE.fullmatch(expected) or expected == "0" * 64:
            errors.append(f"hash:{asset_id}:missing")
            continue
        try:
            path, root = locate_asset(spec, asset_roots)
            observed = observed_asset_hash(spec, path)
        except (FileNotFoundError, ValueError, OSError):
            errors.append(f"asset:{asset_id}:missing_or_symlink")
            continue
        if observed != expected:
            errors.append(f"hash:{asset_id}:mismatch")
            continue
        resolved_assets[asset_id] = str(path)
        resolved_roots[asset_id] = str(root)
        runtime_inventory.append(
            {"id": asset_id, "role": spec.get("role", "asset"), "sha256": observed}
        )

    input_rows: list[dict] = []
    manifest_path = ROOT / manifest_spec.get("relative_path", "")
    if not any(error.startswith(f"hash:{manifest_spec.get('id', 'unknown')}") for error in errors):
        try:
            input_rows = _load_input_rows(manifest_path, asset_roots, errors)
        except (OSError, csv.Error):
            errors.append("manifest:unreadable")
    split_counts = Counter(row["split"] for row in input_rows)
    if len({row["record_id"] for row in input_rows}) != len(input_rows):
        errors.append("manifest:duplicate_record_id")
    input_hash = hashlib.sha256()
    for digest in sorted(row["sha256"] for row in input_rows):
        input_hash.update(bytes.fromhex(digest))
    if len(input_rows) != image_count:
        errors.append("manifest:included_row_count_mismatch")
    expected_splits = manifest_spec.get("split_counts") or {}
    if dict(split_counts) != expected_splits:
        errors.append("manifest:split_counts_mismatch")

    policy = requirements.get("benchmark_policy") or {}
    process_config = build_process_config(device, int(policy.get("thread_count", 1)))
    result = {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "baseline_commit": baseline_commit,
        "actual_commit": actual_commit,
        "tracked_worktree_dirty": dirty,
        "code_state": code_state,
        "requirements_sha256": sha256_file(requirements_path),
        "approval_sha256": sha256_file(approval_path) if approval_path.is_file() else "unavailable",
        "evaluator_sha256": sha256_file(Path(__file__)),
        "worker_sha256": sha256_file(ROOT / "scripts" / "wp01_baseline_worker.py"),
        "input_content_sha256": input_hash.hexdigest(),
        "tracked_inventory": tracked_inventory,
        "runtime_inventory": runtime_inventory,
        "resolved_assets": resolved_assets,
        "resolved_roots": resolved_roots,
        "input_rows": input_rows,
        "input_counts": dict(split_counts),
        "benchmark_policy": policy,
        "process_config": process_config,
        "environment": _environment_metadata(device),
        "approval": approval,
        "invocation": {
            "requirements_path": str(requirements_path.resolve()),
            "approval_path": str(approval_path.resolve()),
            "code_root": str(code_root.resolve()),
            "asset_roots": [str(path.expanduser().resolve()) for path in asset_roots],
            "device": device,
        },
    }
    result["gate_fingerprint"] = gate_fingerprint(result)
    return result


def inventory_assets(requirements_path: Path, asset_roots: list[Path]) -> dict:
    requirements = load_json(requirements_path)
    observed = {}
    for spec in requirements.get("runtime_assets") or []:
        try:
            path, _ = locate_asset(spec, asset_roots)
            observed[spec["id"]] = observed_asset_hash(spec, path)
        except (FileNotFoundError, ValueError, OSError):
            observed[spec.get("id", "unknown")] = None
    for spec in [requirements.get("input_manifest") or {}, *(requirements.get("tracked_evaluator_assets") or [])]:
        path = ROOT / _safe_relative_path(spec.get("relative_path", ""))
        observed[spec.get("id", "unknown")] = sha256_file(path) if path.is_file() else None
    return observed


def execute_run(preflight: dict, code_root: Path) -> Path:
    if not preflight.get("passed"):
        raise PreflightFailure("Preflight failed; OCR worker was not started")
    cleanup_expired_private_artifacts()
    policy = preflight["benchmark_policy"]
    process_config = preflight["process_config"]
    run_id = make_run_id(process_config["device"], process_config)
    run_dir = LOCAL_ROOT / "runs" / run_id
    debug_dir = LOCAL_ROOT / "debug" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    if policy.get("debug_level") == "full":
        debug_dir.mkdir(parents=True, exist_ok=False)

    receipt = {**preflight, "run_id": run_id, "debug_directory": str(debug_dir)}
    receipt_path = run_dir / "preflight_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (run_dir / "retention.json").write_text(
        json.dumps(
            {"delete_after": preflight["approval"]["debug_retention"]["delete_after"]},
            indent=2,
        ),
        encoding="utf-8",
    )
    private_output = run_dir / "private_results.jsonl"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "wp01_baseline_worker.py"),
        "--receipt",
        str(receipt_path),
        "--code-root",
        str(code_root),
        "--output",
        str(private_output),
        "--requirements",
        preflight["invocation"]["requirements_path"],
        "--approval",
        preflight["invocation"]["approval_path"],
        "--device",
        process_config["device"],
    ]
    for root in preflight["invocation"]["asset_roots"]:
        command.extend(["--asset-root", root])
    env = os.environ.copy()
    env.update(process_config["environment"])
    env["WP01_PREFLIGHT_RECEIPT"] = str(receipt_path)
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    return run_dir


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = (len(values) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[lower]
    fraction = index - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def normalize_text(text: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFD", (text or "").lower().strip())
    no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join("".join(ch if ch.isalnum() else " " for ch in no_marks).split())


def _load_evaluator_assets() -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    gt_payload = load_json(ROOT / "data" / "eval" / "gt_drugs_by_image.json")
    gt = {
        row["image_id"]: {item["canonical_id"] for item in row["expected_drugs"]}
        for row in gt_payload["images"]
    }
    alias_payload = load_json(ROOT / "data" / "eval" / "canonical_drug_aliases.json")
    aliases = [
        (row["canonical_id"], normalize_text(alias))
        for row in alias_payload["canonical_drugs"]
        for alias in row["aliases"]
    ]
    aliases.sort(key=lambda item: len(item[1]), reverse=True)
    return gt, aliases


def _prediction_metrics(result: dict, expected: set[str], aliases: list[tuple[str, str]]) -> tuple[int, int, int, bool]:
    matched: set[str] = set()
    unmatched: set[str] = set()
    for medication in result.get("medications", []) if isinstance(result, dict) else []:
        if not isinstance(medication, dict):
            continue
        raw = medication.get("ocr_text") or medication.get("drug_name") or medication.get("matched_drug_name") or ""
        if not raw.strip():
            continue
        normalized = normalize_text(raw)
        canonical = next((cid for cid, alias in aliases if alias and alias in normalized), None)
        if canonical:
            matched.add(canonical)
        else:
            unmatched.add(normalized)
    tp = len(matched & expected)
    fp = len(matched - expected) + len(unmatched)
    fn = len(expected - matched)
    return tp, fp, fn, matched == expected and not unmatched


def _error_category(result: dict) -> str:
    error = str(result.get("error", "")).lower() if isinstance(result, dict) else "invalid"
    if not error:
        return "none"
    if "no text" in error or "empty block" in error:
        return "ocr_empty"
    if "cannot read" in error:
        return "input_read_error"
    if error == "invalid":
        return "invalid_result"
    return "pipeline_error"


def _distribution_summary(values: list[float]) -> dict:
    return {
        "sample_count": len(values),
        "mean": mean(values) if values else 0.0,
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
    }


def _timing_summary(values: list[float]) -> dict:
    summary = _distribution_summary(values)
    return {
        "sample_count": summary["sample_count"],
        "mean_s": summary["mean"],
        "p50_s": summary["p50"],
        "p90_s": summary["p90"],
        "p95_s": summary["p95"],
    }


def _assert_aggregate_safe(payload: object) -> None:
    banned_keys = {"ocr_text", "text", "image", "filename", "path", "crop", "overlay", "relative_path", "original_filename"}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in banned_keys:
                raise ValueError(f"Privacy-unsafe aggregate key: {key}")
            _assert_aggregate_safe(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_aggregate_safe(value)
    elif isinstance(payload, str):
        if payload.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", payload):
            raise ValueError("Absolute path found in aggregate report")


def validate_result_records(
    records: list[dict],
    expected_rows: list[dict],
    repetitions: int,
    *,
    required_split_counts: dict[str, int] | None = None,
) -> None:
    expected_by_id = {}
    for row in expected_rows:
        record_id = row.get("record_id") or row.get("image_id")
        if not record_id or record_id in expected_by_id:
            raise ValueError("WP-01 result contract has duplicate expected IDs")
        expected_by_id[record_id] = row.get("split")
    if required_split_counts and Counter(expected_by_id.values()) != Counter(required_split_counts):
        raise ValueError("WP-01 result contract does not contain the approved 50/120 splits")
    expected_keys = {
        (image_id, repetition)
        for image_id in expected_by_id
        for repetition in range(1, repetitions + 1)
    }
    actual_keys = []
    invalid_split = False
    for record in records:
        record_id = record.get("record_id") or record.get("image_id")
        key = (record_id, record.get("repetition"))
        actual_keys.append(key)
        if expected_by_id.get(record_id) != record.get("split"):
            invalid_split = True
    counts = Counter(actual_keys)
    if (
        set(actual_keys) != expected_keys
        or any(count != 1 for count in counts.values())
        or len(actual_keys) != len(expected_keys)
        or invalid_split
    ):
        raise ValueError("WP-01 result contract violation: missing, extra, duplicate, or invalid row")


def _validate_numeric_map(payload: object, required_fields: Iterable[str]) -> bool:
    if not isinstance(payload, dict) or set(payload) != set(required_fields):
        return False
    return all(
        isinstance(payload[field], (int, float))
        and not isinstance(payload[field], bool)
        and math.isfinite(float(payload[field]))
        and float(payload[field]) >= 0.0
        for field in required_fields
    )


def validate_observation_metrics(records: list[dict], cold_observation: dict) -> None:
    for observation in [cold_observation, *records]:
        if not _validate_numeric_map(
            observation.get("stage_timings_s"), REQUIRED_TIMING_STAGES
        ) or not _validate_numeric_map(
            observation.get("resource_usage"), REQUIRED_RESOURCE_FIELDS
        ):
            raise ValueError("WP-01 timing/resource contract is missing or invalid")
    if not _validate_numeric_map(
        cold_observation.get("initialization_timings_s"),
        REQUIRED_INITIALIZATION_STAGES,
    ):
        raise ValueError("WP-01 timing/resource contract lacks cold initialization evidence")
    cold_total = cold_observation.get("cold_total_s")
    if (
        not isinstance(cold_total, (int, float))
        or isinstance(cold_total, bool)
        or not math.isfinite(float(cold_total))
        or float(cold_total) < 0.0
        or float(cold_total)
        < float(cold_observation["initialization_timings_s"]["initialization_total"])
        + float(cold_observation["stage_timings_s"]["total"])
    ):
        raise ValueError("WP-01 timing/resource contract has an invalid cold total")
    if any("initialization_timings_s" in record or "cold_total_s" in record for record in records):
        raise ValueError("WP-01 timing/resource contract leaked one-time initialization into warm runs")


def _inventory_by_id(receipt: dict) -> dict[str, dict]:
    return {item["id"]: item for item in receipt.get("tracked_inventory", [])}


def verify_evaluator_assets(receipt: dict) -> list[dict]:
    inventory = _inventory_by_id(receipt)
    paths = {
        "ground_truth_50": ROOT / "data" / "eval" / "gt_drugs_by_image.json",
        "canonical_aliases": ROOT / "data" / "eval" / "canonical_drug_aliases.json",
    }
    verified = []
    for asset_id, path in paths.items():
        expected = inventory.get(asset_id, {}).get("sha256")
        if not HASH_RE.fullmatch(str(expected or "")) or not path.is_file():
            raise ValueError(f"Missing evaluator provenance: {asset_id}")
        observed = sha256_file(path)
        if observed != expected:
            raise ValueError(f"Evaluator asset hash mismatch: {asset_id}")
        verified.append({"id": asset_id, "sha256": observed})
    expected_evaluator = receipt.get("evaluator_sha256")
    if expected_evaluator != sha256_file(Path(__file__)):
        raise ValueError("Evaluator source hash mismatch: wp01_baseline_tooling")
    verified.append({"id": "wp01_baseline_tooling", "sha256": expected_evaluator})
    worker_path = ROOT / "scripts" / "wp01_baseline_worker.py"
    expected_worker = receipt.get("worker_sha256")
    if not worker_path.is_file() or expected_worker != sha256_file(worker_path):
        raise ValueError("Worker source hash mismatch: wp01_baseline_worker")
    verified.append({"id": "wp01_baseline_worker", "sha256": expected_worker})
    return verified


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def cleanup_expired_private_artifacts(
    local_root: Path = LOCAL_ROOT,
    *,
    today: date | None = None,
    dry_run: bool = False,
) -> list[str]:
    today = today or date.today()
    local_root = local_root.resolve()
    runs_root = local_root / "runs"
    removed = []
    if not runs_root.is_dir() or runs_root.is_symlink():
        return removed
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir() or run_dir.is_symlink() or not _is_within(run_dir, runs_root):
            continue
        retention_path = run_dir / "retention.json"
        try:
            deadline = date.fromisoformat(str(load_json(retention_path)["delete_after"]))
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if deadline >= today:
            continue
        removed.append(str(run_dir.relative_to(local_root)))
        if not dry_run:
            shutil.rmtree(run_dir)
            debug_dir = local_root / "debug" / run_dir.name
            if debug_dir.is_dir() and not debug_dir.is_symlink() and _is_within(debug_dir, local_root / "debug"):
                shutil.rmtree(debug_dir)
    return removed


def _enforce_report_retention(run_dir: Path, receipt: dict) -> None:
    raw_deadline = (receipt.get("approval", {}).get("debug_retention", {}) or {}).get("delete_after")
    try:
        deadline = date.fromisoformat(str(raw_deadline))
        retention_deadline = date.fromisoformat(
            str(load_json(run_dir / "retention.json")["delete_after"])
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Missing or invalid debug retention deadline") from exc
    if deadline != retention_deadline:
        raise ValueError("Debug retention snapshot does not match the approved receipt")
    if deadline >= date.today():
        return
    if _is_within(run_dir, LOCAL_ROOT / "runs"):
        cleanup_expired_private_artifacts(LOCAL_ROOT)
    raise ValueError("Private artifacts expired and cannot be reported")


def build_aggregate_report(run_dir: Path) -> dict:
    receipt = load_json(run_dir / "preflight_receipt.json")
    _enforce_report_retention(run_dir, receipt)
    evaluator_assets = verify_evaluator_assets(receipt)
    runtime_metadata = load_json(run_dir / "runtime_metadata.json")
    if runtime_metadata.get("gate_fingerprint") != receipt.get("gate_fingerprint"):
        raise ValueError("Runtime metadata does not match the approved preflight")
    if runtime_metadata.get("source_tree_digest") != receipt.get("code_state", {}).get("tree_digest"):
        raise ValueError("Runtime source tree does not match the approved preflight")
    if runtime_metadata.get("worker_sha256") != receipt.get("worker_sha256"):
        raise ValueError("Runtime worker source does not match the approved preflight")
    validate_runtime_bindings(
        {item["id"] for item in receipt.get("runtime_inventory", [])},
        runtime_metadata.get("runtime_bindings", {}),
    )
    records = []
    with (run_dir / "private_results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            records.append(json.loads(line))
    repetitions = int(receipt["benchmark_policy"]["warm_repetitions_per_image"])
    validate_result_records(
        records,
        receipt["input_rows"],
        repetitions,
        required_split_counts={"core_labeled": 50, "extended_unlabeled": 120},
    )
    cold_observation = runtime_metadata.get("cold_observation") or {}
    validate_observation_metrics(records, cold_observation)
    if runtime_metadata.get("cold_total_s") != cold_observation.get("cold_total_s"):
        raise ValueError("Runtime cold total does not match cold initialization evidence")
    primary = {
        record.get("record_id") or record.get("image_id"): record
        for record in records
        if record.get("repetition") == 1
    }
    gt, aliases = _load_evaluator_assets()
    labeled_ids = {row["image_id"] for row in receipt["input_rows"] if row["split"] == "core_labeled"}
    if set(gt) != labeled_ids or len(gt) != 50:
        raise ValueError("Ground truth IDs do not exactly match the 50 labeled inputs")

    tp = fp = fn = exact = 0
    per_record_precision: list[float] = []
    per_record_recall: list[float] = []
    per_record_f1: list[float] = []
    labeled_times: list[float] = []
    operational_times: list[float] = []
    for record in records:
        if record.get("split") == "core_labeled":
            labeled_times.append(float(record["elapsed_s"]))
        elif record.get("split") == "extended_unlabeled":
            operational_times.append(float(record["elapsed_s"]))
    for input_row in receipt["input_rows"]:
        if input_row["split"] != "core_labeled":
            continue
        expected = gt[input_row["image_id"]]
        record = primary[input_row.get("record_id") or input_row["image_id"]]
        row_tp, row_fp, row_fn, row_exact = _prediction_metrics(record["result"], expected, aliases)
        tp += row_tp
        fp += row_fp
        fn += row_fn
        exact += int(row_exact)
        row_precision = row_tp / (row_tp + row_fp) if row_tp + row_fp else 0.0
        row_recall = row_tp / (row_tp + row_fn) if row_tp + row_fn else 0.0
        row_f1 = (
            2 * row_precision * row_recall / (row_precision + row_recall)
            if row_precision + row_recall
            else 0.0
        )
        per_record_precision.append(row_precision)
        per_record_recall.append(row_recall)
        per_record_f1.append(row_f1)
    operational_primary = [
        primary[row.get("record_id") or row["image_id"]]
        for row in receipt["input_rows"]
        if row.get("split") == "extended_unlabeled"
    ]
    errors = Counter(_error_category(record["result"]) for record in operational_primary)
    error_count = len(operational_primary) - errors.get("none", 0)
    empty_count = sum(
        not bool(record["result"].get("medications", []))
        for record in operational_primary
        if isinstance(record.get("result"), dict)
    )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    stage_timings = {
        stage: {
            "cold_first_inference": _timing_summary(
                [float(cold_observation["stage_timings_s"][stage])]
            ),
            "warm": _timing_summary(
                [float(record["stage_timings_s"][stage]) for record in records]
            ),
        }
        for stage in REQUIRED_TIMING_STAGES
    }
    initialization_timings = {
        stage: _timing_summary(
            [float(cold_observation["initialization_timings_s"][stage])]
        )
        for stage in REQUIRED_INITIALIZATION_STAGES
    }
    resource_usage = {
        "units": {
            "process_cpu_s": "seconds",
            "user_cpu_s": "seconds",
            "system_cpu_s": "seconds",
            "max_rss_kb": "kilobytes",
            "voluntary_context_switches": "count",
            "involuntary_context_switches": "count",
        },
        "cold": {
            "scope": "model_initialization_plus_first_inference",
            "metrics": {
                field: float(cold_observation["resource_usage"][field])
                for field in REQUIRED_RESOURCE_FIELDS
            },
        },
        "warm": {
            "sample_count": len(records),
            "metrics": {
                field: _timing_summary(
                    [float(record["resource_usage"][field]) for record in records]
                )
                if field.endswith("_s")
                else _distribution_summary(
                    [float(record["resource_usage"][field]) for record in records]
                )
                for field in REQUIRED_RESOURCE_FIELDS
            },
        },
    }
    approval = receipt["approval"]
    manifest = next(item for item in receipt["tracked_inventory"] if item["id"] == "phase_a_eval_v2_170")
    report = {
        "schema_version": 1,
        "run_id": receipt["run_id"],
        "baseline": {
            "mode": "approved_main",
            "code_commit": receipt["baseline_commit"],
            "source_tree_digest": runtime_metadata["source_tree_digest"],
        },
        "provenance": {
            "requirements_sha256": receipt["requirements_sha256"],
            "manifest": {
                "id": manifest["id"],
                "sha256": manifest["sha256"],
                "input_content_sha256": receipt["input_content_sha256"],
                "record_count": 170,
            },
            "assets": receipt["runtime_inventory"],
            "evaluator_assets": evaluator_assets,
            "runtime_bindings": runtime_metadata["runtime_bindings"],
            "measurement": {
                "stage_clock": "time.perf_counter",
                "resource_source": "resource.getrusage(RUSAGE_SELF)",
                "max_rss_semantics": "process_peak_at_observation_end",
            },
            "seed": receipt["benchmark_policy"]["seed"],
            "warm_repetitions_per_record": receipt["benchmark_policy"]["warm_repetitions_per_image"],
            "thread_policy": {
                "threads": receipt["process_config"]["threads"],
                "variables": sorted(receipt["process_config"]["environment"]),
            },
            "process": {
                "device": receipt["process_config"]["device"],
                "cuda_enabled": receipt["process_config"]["cuda_enabled"],
                "enforcement": receipt["process_config"]["enforcement"],
                "environment": receipt["process_config"]["environment"],
            },
            "environment": receipt["environment"],
            "privacy_approval_reference": approval["privacy_approval"]["reference"],
            "debug_retention_delete_after": approval["debug_retention"]["delete_after"],
        },
        "correctness_labeled_50": {
            "record_count": len(gt),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "micro_precision": precision,
            "micro_recall": recall,
            "micro_f1": f1,
            "macro_precision": mean(per_record_precision),
            "macro_recall": mean(per_record_recall),
            "macro_f1": mean(per_record_f1),
            "exact_match_count": exact,
            "exact_match_rate": exact / len(gt) if gt else 0.0,
            "timing": _timing_summary(labeled_times),
        },
        "operational_unlabeled_120": {
            "record_count": len(operational_primary),
            "success_count": len(operational_primary) - error_count,
            "error_count": error_count,
            "empty_count": empty_count,
            "success_rate": (len(operational_primary) - error_count) / len(operational_primary) if operational_primary else 0.0,
            "empty_rate": empty_count / len(operational_primary) if operational_primary else 0.0,
            "error_categories": {key: value for key, value in sorted(errors.items()) if key != "none"},
            "timing": _timing_summary(operational_times),
        },
        "stage_timings": stage_timings,
        "initialization_timings": initialization_timings,
        "resource_usage": resource_usage,
        "cold_start": {
            "scope": "model_initialization_plus_first_inference",
            "total_s": float(cold_observation["cold_total_s"]),
        },
        "debug": {"level": receipt["benchmark_policy"]["debug_level"], "tracked_artifacts": False},
    }
    _assert_aggregate_safe(report)
    return report


def _parse_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--asset-root", action="append", type=Path, default=[])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory", help="Observe hashes without running OCR")
    _parse_common(inventory)
    for command in ("preflight", "run"):
        child = subparsers.add_parser(command)
        _parse_common(child)
        child.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
        child.add_argument("--code-root", type=Path, required=True)
        child.add_argument("--device", choices=("cpu", "gpu"), required=True)
    report = subparsers.add_parser("report")
    report.add_argument("--run-dir", type=Path, required=True)
    report.add_argument("--output", type=Path)
    cleanup = subparsers.add_parser("cleanup", help="Delete expired ignored WP-01 private artifacts")
    cleanup.add_argument("--local-root", type=Path, default=LOCAL_ROOT)
    cleanup.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "inventory":
        print(json.dumps(inventory_assets(args.requirements, args.asset_root), indent=2, sort_keys=True))
        return 0
    if args.command == "report":
        payload = build_aggregate_report(args.run_dir)
        output = args.output or REPORT_ROOT / f"{payload['run_id']}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Aggregate report written: {output.relative_to(ROOT)}")
        return 0
    if args.command == "cleanup":
        removed = cleanup_expired_private_artifacts(args.local_root, dry_run=args.dry_run)
        for relative in removed:
            print(relative)
        return 0
    preflight = run_preflight(
        args.requirements,
        args.approval,
        args.code_root,
        args.asset_root,
        args.device,
    )
    if not preflight["passed"]:
        print("PREFLIGHT BLOCKED")
        for error in preflight["errors"]:
            print(f"- {error}")
        return 2
    print("PREFLIGHT PASS")
    if args.command == "run":
        run_dir = execute_run(preflight, args.code_root)
        print(f"Private run directory: {run_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

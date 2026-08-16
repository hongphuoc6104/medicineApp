#!/usr/bin/env python3
"""
P13: Environment & Reproducibility Capture Script for RxIE Pre-Training Sprint.
Captures hardware, software, git commit, dataset checksums, and model revisions into reports/pretraining/environment.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent


def get_git_commit() -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(root_dir),
        )
        return res.stdout.strip()
    except Exception:
        return None


def get_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def capture_env() -> dict:
    dataset_dir = root_dir / "data" / "ner_dataset"

    # PyTorch and CUDA details
    import torch
    import transformers
    import tokenizers
    import datasets
    import seqeval
    import pydantic

    cuda_info = {
        "available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "cudnn_version": torch.backends.cudnn.version() if torch.cuda.is_available() else None,
    }

    import importlib.metadata

    def get_pkg_version(pkg_name: str, mod: Any = None) -> str:
        try:
            return importlib.metadata.version(pkg_name)
        except Exception:
            return getattr(mod, "__version__", "unknown") if mod else "unknown"

    env_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "hardware": {
            "cpu_count": os.cpu_count(),
            "cuda": cuda_info,
        },
        "frameworks": {
            "torch": get_pkg_version("torch", torch),
            "transformers": get_pkg_version("transformers", transformers),
            "tokenizers": get_pkg_version("tokenizers", tokenizers),
            "datasets": get_pkg_version("datasets", datasets),
            "seqeval": get_pkg_version("seqeval", seqeval),
            "pydantic": get_pkg_version("pydantic", pydantic),
        },
        "reproducibility": {
            "git_commit": get_git_commit(),
            "dataset_version": "rxie-dataset-v1.0.1",
            "dataset_checksums": {
                "train.jsonl": get_sha256(dataset_dir / "train.jsonl"),
                "val.jsonl": get_sha256(dataset_dir / "val.jsonl"),
                "test.jsonl": get_sha256(dataset_dir / "test.jsonl"),
                "bio_train.jsonl": get_sha256(dataset_dir / "bio_train.jsonl"),
                "bio_val.jsonl": get_sha256(dataset_dir / "bio_val.jsonl"),
                "bio_test.jsonl": get_sha256(dataset_dir / "bio_test.jsonl"),
            },
            "model_revisions": {
                "phobert": "vinai/phobert-base-v2",
                "bamibert": "Qualcomm-AI-Research/BamiBERT",
                "vipubmeddeberta": "manhtt-079/vipubmed-deberta-base",
            },
        },
    }
    return env_record


def main() -> None:
    out_dir = root_dir / "reports" / "pretraining"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "environment.json"

    env_data = capture_env()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(env_data, f, ensure_ascii=False, indent=2)

    # Also export requirements-lock.txt via pip list
    try:
        pip_res = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
        )
        if pip_res.returncode == 0:
            (root_dir / "requirements-lock.txt").write_text(pip_res.stdout, encoding="utf-8")
    except Exception:
        pass

    print(f"[+] Exported Environment & Reproducibility Record -> {out_path}")
    print(f"    - Python: {env_data['system']['python_version']}")
    print(f"    - PyTorch: {env_data['frameworks']['torch']} (CUDA: {env_data['hardware']['cuda']['available']})")
    print(f"    - Git Commit: {env_data['reproducibility']['git_commit']}")


if __name__ == "__main__":
    main()

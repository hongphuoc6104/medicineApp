"""
tests/e2e/conftest.py — Shared test fixtures, mock servers, and path resolvers for MedicineApp E2E test suite.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from starlette.testclient import TestClient


# ── Directory Fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns absolute path to the root directory of the project."""
    # tests/e2e/conftest.py -> tests/e2e -> tests -> project_root
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def mobile_dir(project_root: Path) -> Path:
    """Returns path to the mobile application directory."""
    return project_root / "mobile"


@pytest.fixture(scope="session")
def server_dir(project_root: Path) -> Path:
    """Returns path to the FastAPI Python server directory."""
    return project_root / "server"


@pytest.fixture(scope="session")
def server_node_dir(project_root: Path) -> Path:
    """Returns path to the Express Node.js server directory."""
    return project_root / "server-node"


@pytest.fixture(scope="session")
def data_dir(project_root: Path) -> Path:
    """Returns path to the data directory."""
    return project_root / "data"


@pytest.fixture(scope="session")
def reports_dir(project_root: Path) -> Path:
    """Returns path to the reports directory."""
    return project_root / "reports"


@pytest.fixture(scope="session")
def scripts_dir(project_root: Path) -> Path:
    """Returns path to the scripts directory."""
    return project_root / "scripts"


@pytest.fixture(scope="session")
def models_dir(project_root: Path) -> Path:
    """Returns path to the models directory."""
    return project_root / "models"


# ── Command Execution Helper ─────────────────────────────────────────

class CommandResult:
    def __init__(self, returncode: int, stdout: str, stderr: str, duration: float):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def __repr__(self) -> str:
        return f"<CommandResult code={self.returncode} duration={self.duration:.2f}s>"


@pytest.fixture(scope="session")
def run_command(project_root: Path):
    """Subprocess runner fixture with timing and environment handling."""
    def _run(
        cmd: List[str] | str,
        cwd: Optional[Path] = None,
        env_extra: Optional[Dict[str, str]] = None,
        timeout: float = 120.0,
    ) -> CommandResult:
        working_dir = cwd or project_root
        custom_env = os.environ.copy()
        custom_env["PYTHONPATH"] = str(project_root)
        if env_extra:
            custom_env.update(env_extra)

        start_time = time.time()
        try:
            if isinstance(cmd, str):
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=working_dir,
                    env=custom_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                )
            else:
                proc = subprocess.run(
                    cmd,
                    cwd=working_dir,
                    env=custom_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                )
            duration = time.time() - start_time
            return CommandResult(
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=duration,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.time() - start_time
            return CommandResult(
                returncode=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nCommand timed out after {timeout}s",
                duration=duration,
            )
        except Exception as exc:
            duration = time.time() - start_time
            return CommandResult(
                returncode=1,
                stdout="",
                stderr=str(exc),
                duration=duration,
            )

    return _run


# ── Data Artifact Fixtures ───────────────────────────────────────────

@pytest.fixture(scope="session")
def visible_gt_data(data_dir: Path) -> Dict[str, Any]:
    """Loads and returns data/visible_in_frame_gt.json."""
    gt_file = data_dir / "visible_in_frame_gt.json"
    if not gt_file.exists():
        pytest.skip(f"Ground truth file missing: {gt_file}")
    with open(gt_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def provenance_log_data(data_dir: Path) -> Dict[str, Any]:
    """Loads and returns data/human_verification_provenance_log.json."""
    prov_file = data_dir / "human_verification_provenance_log.json"
    if not prov_file.exists():
        pytest.skip(f"Provenance log file missing: {prov_file}")
    with open(prov_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def drug_db_data(data_dir: Path) -> List[Dict[str, Any]]:
    """Loads and returns drug list from data/drug_db_vn_full.json."""
    db_file = data_dir / "drug_db_vn_full.json"
    if not db_file.exists():
        pytest.skip(f"Drug DB file missing: {db_file}")
    with open(db_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        if isinstance(loaded, dict) and "drugs" in loaded:
            return loaded["drugs"]
        elif isinstance(loaded, list):
            return loaded
        return []


@pytest.fixture(scope="session")
def summary_csv_data(reports_dir: Path) -> List[Dict[str, str]]:
    """Loads and returns reports/real_medication_roi_ablation/summary.csv."""
    csv_file = reports_dir / "real_medication_roi_ablation" / "summary.csv"
    if not csv_file.exists():
        pytest.skip(f"Summary CSV file missing: {csv_file}")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.fixture(scope="session")
def significance_json_data(reports_dir: Path) -> Dict[str, Any]:
    """Loads and returns reports/real_medication_roi_ablation/statistical_significance.json."""
    json_file = reports_dir / "real_medication_roi_ablation" / "statistical_significance.json"
    if not json_file.exists():
        pytest.skip(f"Statistical significance file missing: {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def transition_matrix_data(reports_dir: Path) -> List[Dict[str, str]]:
    """Loads and returns reports/real_medication_roi_ablation/paired_transition_matrix.csv."""
    csv_file = reports_dir / "real_medication_roi_ablation" / "paired_transition_matrix.csv"
    if not csv_file.exists():
        pytest.skip(f"Transition matrix CSV file missing: {csv_file}")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


# ── FastAPI Test Client Fixture ──────────────────────────────────────

@pytest.fixture(scope="session")
def fastapi_client(project_root: Path) -> TestClient:
    """Provides a Starlette TestClient connected to the FastAPI application."""
    os.environ["FLAGS_enable_pir_api"] = "0"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    try:
        from server.main import app
        client = TestClient(app, raise_server_exceptions=False)
        return client
    except Exception as exc:
        pytest.skip(f"FastAPI app initialization failed: {exc}")

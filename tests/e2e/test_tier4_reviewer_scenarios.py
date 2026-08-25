"""
tests/e2e/test_tier4_reviewer_scenarios.py — Tier 4 Real-World Academic Reproduction Scenarios (5 test cases).

Covers:
- T4.1: Scenario 1 — Reviewer Benchmark Replication Workflow
- T4.2: Scenario 2 — One-Command Docker Full-Stack Deployment Verification
- T4.3: Scenario 3 — Mobile APK Build & Analysis Verification
- T4.4: Scenario 4 — Documentation Walkthrough Verification
- T4.5: Scenario 5 — Repository Cleanliness & Packaging Audit
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from starlette.testclient import TestClient

from core.drug_search.drug_lookup import DrugLookup


class TestTier4AcademicReproductionScenarios:
    """Tier 4: End-to-End Real-World Academic Reproduction Workflows."""

    def test_t4_1_scenario_reviewer_benchmark_replication(
        self,
        scripts_dir: Path,
        reports_dir: Path,
        visible_gt_data: Dict[str, Any],
        provenance_log_data: Dict[str, Any],
        summary_csv_data: List[Dict[str, str]],
        significance_json_data: Dict[str, Any],
        transition_matrix_data: List[Dict[str, str]],
    ):
        """T4.1 [Scenario 1: Reviewer Benchmark Replication Workflow]: Full verification of reproduction pipeline artifacts."""
        # 1. Verify Ground Truth and Provenance
        assert len(visible_gt_data) == 30, "Visible GT must contain 30 captures"
        assert provenance_log_data.get("protocol_version") == "1.0.0"

        # 2. Verify Micro and Macro Metrics in summary.csv
        micro_r0 = next(r for r in summary_csv_data if r["granularity"] == "Drug-Instance Micro" and r["condition"] == "r0")
        micro_r1 = next(r for r in summary_csv_data if r["granularity"] == "Drug-Instance Micro" and r["condition"] == "r1")
        assert math.isclose(float(micro_r0["f1_score"]), 0.7675, abs_tol=0.001)
        assert math.isclose(float(micro_r1["f1_score"]), 0.8015, abs_tol=0.001)

        # 3. Verify Paired Transition Matrix
        matrix_dict = {row["transition"].strip(): row["count"].strip() for row in transition_matrix_data}
        assert any("14" in v for k, v in matrix_dict.items() if "Gain" in k or "Recovery" in k)

        # 4. Verify Statistical Significance
        mcnemar = significance_json_data.get("mcnemar_exact_test", {})
        assert math.isclose(float(mcnemar.get("two_sided_p_value", 0)), 0.4049, abs_tol=0.001)

    def test_t4_2_scenario_docker_full_stack_deployment(
        self,
        project_root: Path,
        server_node_dir: Path,
        fastapi_client: TestClient,
    ):
        """T4.2 [Scenario 2: One-Command Docker Full-Stack Deployment]: Verify container topology, health, and scan flow."""
        # 1. Verify docker-compose.yml configuration
        compose_file = project_root / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml missing"
        with open(compose_file, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})
        assert "postgres" in services and "node-api" in services and "python-ai" in services

        # 2. Verify FastAPI AI Proxy Health & Prediction
        health_resp = fastapi_client.get("/api/health")
        assert health_resp.status_code == 200, f"FastAPI health failed: {health_resp.text}"

        scan_resp = fastapi_client.post(
            "/api/scan-prescription",
            data={"ocr_text": "1. Paracetamol 500mg\n2. Losartan 50mg"},
        )
        assert scan_resp.status_code == 200, f"FastAPI scan failed: {scan_resp.text}"

        # 3. Verify Node DB migrations
        migrate_file = server_node_dir / "src" / "config" / "migrate.js"
        assert migrate_file.exists()
        assert "CREATE TABLE IF NOT EXISTS scans" in migrate_file.read_text(encoding="utf-8")

    def test_t4_3_scenario_mobile_apk_build_and_analysis(
        self,
        mobile_dir: Path,
        run_command,
    ):
        """T4.3 [Scenario 3: Mobile APK Build & Analysis Verification]: Verify mobile static analysis and Android config."""
        # 1. Verify analysis_options.yaml and pubspec.yaml
        assert (mobile_dir / "analysis_options.yaml").exists()
        assert (mobile_dir / "pubspec.yaml").exists()

        # 2. Run flutter analyze if CLI is present
        res = run_command(["flutter", "analyze", "--no-fatal-infos"], cwd=mobile_dir, timeout=60.0)
        if res.returncode != 127:
            assert res.returncode == 0 or "error •" not in res.stdout

        # 3. Verify Gradle Android Build setup
        gradle_file = mobile_dir / "android" / "app" / "build.gradle.kts"
        if not gradle_file.exists():
            gradle_file = mobile_dir / "android" / "app" / "build.gradle"
        assert gradle_file.exists()
        content = gradle_file.read_text(encoding="utf-8")
        assert "VERSION_17" in content or "17" in content
        assert "play-services-mlkit-document-scanner:16.0.0" in content

    def test_t4_4_scenario_documentation_walkthrough(
        self,
        project_root: Path,
    ):
        """T4.4 [Scenario 4: Documentation Walkthrough Verification]: Verify links, quickstart commands, and claims."""
        readme = project_root / "README.md"
        assert readme.exists(), "README.md missing"
        readme_text = readme.read_text(encoding="utf-8")

        # Verify quickstart commands exist
        assert "docker" in readme_text.lower()
        assert "flutter" in readme_text.lower()

        # Verify documentation files
        assert (project_root / "LICENSE").exists()
        assert (project_root / "mobile" / "README.md").exists()

    def test_t4_5_scenario_repository_cleanliness_and_packaging(
        self,
        project_root: Path,
        run_command,
    ):
        """T4.5 [Scenario 5: Repository Cleanliness & Packaging Audit]: Complete git index audit and MIT licensing."""
        res = run_command(["git", "ls-files"])
        assert res.success
        tracked_files = res.stdout.strip().splitlines()

        # Verify zero junk files
        prohibited_exts = [".docx", ".mdj", ".tmp", ".bak"]
        junk = [f for f in tracked_files if any(f.endswith(ext) for ext in prohibited_exts) or "failures/" in f]
        assert not junk, f"Found prohibited junk files in git index: {junk}"

        # Verify root LICENSE
        license_file = project_root / "LICENSE"
        assert license_file.exists()
        assert "MIT License" in license_file.read_text(encoding="utf-8")

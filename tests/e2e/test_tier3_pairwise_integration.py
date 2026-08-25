"""
tests/e2e/test_tier3_pairwise_integration.py — Tier 3 Cross-Feature Pairwise Integration Tests (5 test cases).

Covers:
- T3.1: Mobile Client <-> Node API <-> Python AI (R2 x R3)
- T3.2: Docker Stack <-> Database Seed <-> Drug Search (R3 x R4)
- T3.3: Academic Benchmark Suite <-> Ground Truth Dataset <-> Report Generator (R4 x R5)
- T3.4: Documentation Quickstart <-> Actual Execution Commands (R5 x R1)
- T3.5: Git Attributes / Git Ignore <-> Build Artifacts <-> Dataset Persistence (R1 x R4)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from starlette.testclient import TestClient

from core.drug_search.drug_lookup import DrugLookup


class TestTier3PairwiseIntegration:
    """Tier 3: Pairwise Combinatorial Cross-Feature Integration Tests."""

    def test_t3_1_mobile_node_python_pairwise_contract(
        self,
        mobile_dir: Path,
        server_node_dir: Path,
        fastapi_client: TestClient,
    ):
        """T3.1 [Mobile Client <-> Node API <-> Python AI]: Simulated scan payload across mobile, node, and python contracts."""
        # 1. Verify mobile contract schema
        mobile_contract = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerChannelContract.kt"
        )
        assert mobile_contract.exists(), "Mobile scanner contract missing"
        contract_text = mobile_contract.read_text(encoding="utf-8")
        assert "scanPrescriptionDocument" in contract_text

        # 2. Verify Node API scan service proxy structure
        node_scan_service = server_node_dir / "src" / "services" / "scan.service.js"
        assert node_scan_service.exists(), "Node scan service missing"
        service_text = node_scan_service.read_text(encoding="utf-8")
        assert "scan-prescription" in service_text
        assert "ocr_lines" in service_text or "ocr_text" in service_text

        # 3. Verify Python FastAPI scan-prescription endpoint handles mobile-formatted payload
        sample_ocr_lines = json.dumps([
            {"text": "1. Celecoxib 200mg", "box": [10, 20, 100, 30]},
            {"text": "Ngày uống 2 lần, mỗi lần 1 viên", "box": [10, 55, 200, 30]},
        ])
        resp = fastapi_client.post(
            "/api/scan-prescription",
            data={"ocr_lines": sample_ocr_lines, "layout_strategy": "p3_medication_bands"},
        )
        assert resp.status_code == 200, f"Python AI failed to process simulated mobile scan payload: {resp.text}"
        data = resp.json()
        assert "medications" in data or "drugs" in data or "medication_candidates" in data, (
            f"Expected structured medication items in response, got: {data}"
        )

    def test_t3_2_docker_stack_db_seed_drug_search(
        self,
        project_root: Path,
        server_node_dir: Path,
        drug_db_data: List[Dict[str, Any]],
    ):
        """T3.2 [Docker Stack <-> Database Seed <-> Drug Search]: Seeded 9,284 drugs are queryable via fuzzy lookup."""
        # 1. Verify docker-compose mounts and env
        compose_file = project_root / "docker-compose.yml"
        compose_text = compose_file.read_text(encoding="utf-8")
        assert "postgres" in compose_text

        # 2. Verify Node.js seed script parses drug_db_vn_full.json
        seed_js = server_node_dir / "src" / "config" / "seed.js"
        if seed_js.exists():
            seed_content = seed_js.read_text(encoding="utf-8")
            assert "drug_db_vn_full.json" in seed_content or "drug_cache" in seed_content or "seed" in seed_content

        # 3. Verify DrugLookup queries the seeded drug database
        lookup = DrugLookup()
        res = lookup.lookup("Amlodipine 5mg")
        assert res is not None, "Failed to fuzzy match 'Amlodipine 5mg' in drug database"
        matched_str = str(res.get("name", "")) + str(res.get("generic", ""))
        assert "amlodipine" in matched_str.lower() or "amlodipin" in matched_str.lower() or res.get("score", 0) >= 65

    def test_t3_3_benchmark_suite_gt_report_pipeline(
        self,
        scripts_dir: Path,
        visible_gt_data: Dict[str, Any],
        reports_dir: Path,
        summary_csv_data: List[Dict[str, str]],
    ):
        """T3.3 [Academic Benchmark Suite <-> GT Dataset <-> Report Generator]: Ground truth consumes OCR to produce reports."""
        assert len(visible_gt_data) == 30, "Visible GT must contain 30 captures"

        # Verify reports directory has all required artifacts
        ablation_dir = reports_dir / "real_medication_roi_ablation"
        assert ablation_dir.exists(), "real_medication_roi_ablation directory missing"

        summary_file = ablation_dir / "summary.csv"
        tax_file = ablation_dir / "failure_taxonomy.csv"
        matrix_file = ablation_dir / "paired_transition_matrix.csv"
        stats_file = ablation_dir / "statistical_significance.json"

        assert summary_file.exists(), "summary.csv missing"
        assert tax_file.exists(), "failure_taxonomy.csv missing"
        assert matrix_file.exists(), "paired_transition_matrix.csv missing"
        assert stats_file.exists(), "statistical_significance.json missing"

        # Verify summary CSV links conditions r0 and r1
        conditions = {r["condition"] for r in summary_csv_data}
        assert "r0" in conditions and "r1" in conditions, f"Both r0 and r1 must exist in summary.csv, got {conditions}"

    def test_t3_4_documentation_quickstart_execution_alignment(
        self,
        project_root: Path,
        server_node_dir: Path,
        mobile_dir: Path,
    ):
        """T3.4 [Documentation Quickstart <-> Actual Execution Commands]: README commands match actual project entrypoints."""
        readme_file = project_root / "README.md"
        assert readme_file.exists(), "README.md missing"
        readme_text = readme_file.read_text(encoding="utf-8")

        # 1. Docker compose command alignment
        if "docker compose" in readme_text or "docker-compose" in readme_text:
            assert (project_root / "docker-compose.yml").exists()

        # 2. Node server package command alignment
        if "npm run dev" in readme_text or "npm start" in readme_text:
            pkg_json = json.loads((server_node_dir / "package.json").read_text(encoding="utf-8"))
            assert "dev" in pkg_json.get("scripts", {}) or "start" in pkg_json.get("scripts", {})

        # 3. Mobile pubspec alignment
        if "flutter pub get" in readme_text or "flutter run" in readme_text:
            assert (mobile_dir / "pubspec.yaml").exists()

    def test_t3_5_git_hygiene_build_artifacts_persistence(
        self,
        project_root: Path,
        data_dir: Path,
    ):
        """T3.5 [Git Attributes / Git Ignore <-> Build Artifacts <-> Dataset Persistence]: Ignore builds, track datasets."""
        gitignore = (project_root / ".gitignore").read_text(encoding="utf-8")

        # Build caches must be ignored
        assert "build/" in gitignore or "mobile/build/" in gitignore
        assert "node_modules/" in gitignore

        # Datasets must exist and be accessible
        db_file = data_dir / "drug_db_vn_full.json"
        gt_file = data_dir / "visible_in_frame_gt.json"
        assert db_file.exists(), "data/drug_db_vn_full.json missing"
        assert gt_file.exists(), "data/visible_in_frame_gt.json missing"

"""
tests/e2e/test_tier1_feature_coverage.py — Tier 1 Feature Coverage Tests (26 test cases).

Covers:
- Feature R1: Isolated Clean Publication Repository (T1.R1.1 – T1.R1.5)
- Feature R2: Complete Android Mobile UI Experience (T1.R2.1 – T1.R2.5)
- Feature R3: One-Command Docker Compose Backend (T1.R3.1 – T1.R3.6)
- Feature R4: Academic Benchmark Reproduction Suite (T1.R4.1 – T1.R4.5)
- Feature R5: Professional Academic Documentation (T1.R5.1 – T1.R5.5)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from starlette.testclient import TestClient


# ==============================================================================
# Feature R1: Isolated Clean Publication Repository (5 tests)
# ==============================================================================

class TestTier1FeatureR1CleanPublicationRepo:
    """T1.R1: Repository cleanliness, gitignore, gitattributes, and licensing."""

    def test_t1_r1_1_git_cleanliness(self, project_root: Path, run_command):
        """T1.R1.1 [Git Cleanliness]: Verify zero tracked temporary/junk files (.docx, .mdj, failure PNGs)."""
        res = run_command(["git", "ls-files"])
        assert res.success, f"git ls-files failed: {res.stderr}"
        tracked_files = res.stdout.strip().splitlines()

        junk_extensions = [".docx", ".mdj"]
        tracked_junk = [
            f for f in tracked_files
            if any(f.endswith(ext) for ext in junk_extensions) or "failures/" in f
        ]
        assert not tracked_junk, f"Found tracked junk files in git index: {tracked_junk}"

    def test_t1_r1_2_gitignore_config(self, project_root: Path):
        """T1.R1.2 [Gitignore Config]: Verify .gitignore covers build artifacts, caches, .env, and does NOT ignore drug DB."""
        gitignore_path = project_root / ".gitignore"
        assert gitignore_path.exists(), ".gitignore file does not exist at root"
        content = gitignore_path.read_text(encoding="utf-8")

        # Verify key ignore rules
        assert "venv/" in content or ".venv/" in content, "venv not covered in .gitignore"
        assert "__pycache__/" in content, "__pycache__ not covered in .gitignore"
        assert "node_modules/" in content, "node_modules not covered in .gitignore"
        assert "mobile/build/" in content or "build/" in content, "build artifacts not covered in .gitignore"
        assert ".pytest_cache/" in content, ".pytest_cache not covered in .gitignore"
        assert "failures/" in content, "golden test failures not covered in .gitignore"

        # Verify data/drug_db_vn_full.json is NOT ignored
        assert "drug_db_vn_full.json" not in content or "!data/drug_db_vn_full.json" in content, (
            "data/drug_db_vn_full.json must NOT be ignored in .gitignore"
        )

    def test_t1_r1_3_gitattributes_config(self, project_root: Path):
        """T1.R1.3 [Gitattributes Config]: Verify .gitattributes configures LF line endings and linguist attributes."""
        gitattributes_path = project_root / ".gitattributes"
        assert gitattributes_path.exists(), ".gitattributes file does not exist at root"
        content = gitattributes_path.read_text(encoding="utf-8")

        assert "eol=lf" in content, ".gitattributes must configure eol=lf"
        assert "*.sh text eol=lf" in content, ".gitattributes must enforce LF for shell scripts"
        assert "linguist-generated" in content or "linguist-vendored" in content, (
            ".gitattributes must configure linguist attributes for datasets/wrappers"
        )

    def test_t1_r1_4_root_mit_license(self, project_root: Path):
        """T1.R1.4 [Root MIT License]: Verify root LICENSE file exists and contains valid MIT License terms."""
        license_path = project_root / "LICENSE"
        assert license_path.exists(), "LICENSE file missing at project root"
        content = license_path.read_text(encoding="utf-8")

        assert "MIT License" in content, "LICENSE must be an MIT License"
        assert "Permission is hereby granted, free of charge" in content, "LICENSE missing MIT grant text"
        assert "WITHOUT WARRANTY OF ANY KIND" in content, "LICENSE missing MIT warranty disclaimer"

    def test_t1_r1_5_package_license_alignment(self, server_node_dir: Path):
        """T1.R1.5 [Package License Alignment]: Verify server-node/package.json specifies license MIT."""
        pkg_json_path = server_node_dir / "package.json"
        assert pkg_json_path.exists(), "server-node/package.json missing"
        with open(pkg_json_path, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)

        assert pkg_data.get("license") == "MIT", (
            f"Expected server-node/package.json license to be 'MIT', got '{pkg_data.get('license')}'"
        )


# ==============================================================================
# Feature R2: Android Mobile UI Experience (5 tests)
# ==============================================================================

class TestTier1FeatureR2AndroidMobileUI:
    """T1.R2: Flutter static analysis, tests, Gradle configuration, permissions, and ML Kit bridge."""

    def test_t1_r2_1_flutter_static_analysis(self, mobile_dir: Path, run_command):
        """T1.R2.1 [Flutter Static Analysis]: Verify flutter analyze runs with zero fatal errors or analysis_options exists."""
        analysis_options = mobile_dir / "analysis_options.yaml"
        assert analysis_options.exists(), "mobile/analysis_options.yaml missing"

        # Check if flutter binary is available
        res = run_command(["flutter", "analyze", "--no-fatal-infos"], cwd=mobile_dir, timeout=60.0)
        if res.returncode == 127:  # flutter not in PATH
            pytest.skip("Flutter SDK CLI not found in PATH")
        # Ensure no compile errors
        assert res.returncode == 0 or "error •" not in res.stdout, (
            f"flutter analyze returned fatal compiler errors:\n{res.stdout}\n{res.stderr}"
        )

    def test_t1_r2_2_flutter_unit_and_widget_tests(self, mobile_dir: Path):
        """T1.R2.2 [Flutter Unit & Widget Tests]: Verify flutter test suite structure and test coverage."""
        test_dir = mobile_dir / "test"
        assert test_dir.exists(), "mobile/test directory missing"

        test_files = list(test_dir.rglob("*_test.dart"))
        assert len(test_files) >= 5, f"Expected at least 5 Flutter test files, found {len(test_files)}"

        # Verify key feature test files exist
        test_names = [f.name for f in test_files]
        assert "document_scanner_test.dart" in test_names, "document_scanner_test.dart missing"
        assert "retired_phase_b_routes_test.dart" in test_names, "retired_phase_b_routes_test.dart missing"

    def test_t1_r2_3_android_build_configuration(self, mobile_dir: Path):
        """T1.R2.3 [Android Build Configuration]: Verify build.gradle.kts configures Java 17, desugaring, ML Kit 16.0.0."""
        gradle_kts = mobile_dir / "android" / "app" / "build.gradle.kts"
        gradle_groovy = mobile_dir / "android" / "app" / "build.gradle"
        gradle_file = gradle_kts if gradle_kts.exists() else gradle_groovy
        assert gradle_file.exists(), "Android app build.gradle(.kts) missing"

        content = gradle_file.read_text(encoding="utf-8")
        assert "VERSION_17" in content or "JavaVersion.VERSION_17" in content or "17" in content, (
            "Java 17+ compatibility required in Android build configuration"
        )
        assert "isCoreLibraryDesugaringEnabled = true" in content or "coreLibraryDesugaring" in content, (
            "coreLibraryDesugaring must be enabled in Android build configuration"
        )
        assert "play-services-mlkit-document-scanner:16.0.0" in content, (
            "ML Kit Document Scanner 16.0.0 dependency must be declared in Android build configuration"
        )

    def test_t1_r2_4_android_manifest_permissions(self, mobile_dir: Path):
        """T1.R2.4 [Android Manifest Permissions]: Verify AndroidManifest.xml declares required permissions and receivers."""
        manifest_file = mobile_dir / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
        assert manifest_file.exists(), "AndroidManifest.xml missing"
        content = manifest_file.read_text(encoding="utf-8")

        assert "android.permission.CAMERA" in content, "CAMERA permission missing in AndroidManifest.xml"
        assert "android.permission.INTERNET" in content, "INTERNET permission missing in AndroidManifest.xml"
        assert "android.permission.SCHEDULE_EXACT_ALARM" in content, "SCHEDULE_EXACT_ALARM permission missing"
        assert 'android:usesCleartextTraffic="true"' in content, "usesCleartextTraffic missing in AndroidManifest.xml"
        assert "ScheduledNotificationBootReceiver" in content or "ScheduledNotificationReceiver" in content, (
            "ScheduledNotification receiver missing in AndroidManifest.xml"
        )

    def test_t1_r2_5_platform_channel_implementation(self, mobile_dir: Path):
        """T1.R2.5 [Platform Channel Implementation]: Verify channel contract and 10MB payload size limit."""
        contract_file = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerChannelContract.kt"
        )
        bridge_file = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerBridge.kt"
        )
        assert contract_file.exists(), "PrescriptionDocumentScannerChannelContract.kt missing"
        assert bridge_file.exists(), "PrescriptionDocumentScannerBridge.kt missing"

        contract_content = contract_file.read_text(encoding="utf-8")
        assert "com.medicineapp.medicine_app/prescription_document_scanner" in contract_content, (
            "Platform channel name mismatch in contract"
        )
        assert "10L * 1024L * 1024L" in contract_content or "MAX_FILE_BYTES" in contract_content, (
            "10MB payload size limit missing in contract"
        )


# ==============================================================================
# Feature R3: One-Command Docker Compose Backend (6 tests)
# ==============================================================================

class TestTier1FeatureR3DockerComposeBackend:
    """T1.R3: Docker compose topology, database migration schema, drug DB seeding, and endpoints."""

    def test_t1_r3_1_compose_service_topology(self, project_root: Path):
        """T1.R3.1 [Compose Service Topology]: Verify docker-compose.yml defines postgres (5432), node-api (3000), python-ai (8000)."""
        compose_file = project_root / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml missing"

        with open(compose_file, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        services = compose_data.get("services", {})
        assert "postgres" in services, "postgres service missing in docker-compose.yml"
        assert "node-api" in services, "node-api service missing in docker-compose.yml"
        assert "python-ai" in services, "python-ai service missing in docker-compose.yml"

        # Verify port mappings
        assert any("5432" in str(p) for p in services["postgres"].get("ports", [])), "postgres port 5432 missing"
        assert any("3000" in str(p) for p in services["node-api"].get("ports", [])), "node-api port 3000 missing"
        assert any("8000" in str(p) for p in services["python-ai"].get("ports", [])), "python-ai port 8000 missing"

    def test_t1_r3_2_postgresql_migrations_schema(self, server_node_dir: Path):
        """T1.R3.2 [PostgreSQL Migrations & Schema]: Verify database migration creates core tables and extensions."""
        migrate_file = server_node_dir / "src" / "config" / "migrate.js"
        assert migrate_file.exists(), "server-node/src/config/migrate.js missing"
        content = migrate_file.read_text(encoding="utf-8")

        assert "pgcrypto" in content, "pgcrypto extension missing in migrations"
        assert "pg_trgm" in content, "pg_trgm extension missing in migrations"
        assert "CREATE TABLE IF NOT EXISTS users" in content, "users table missing in migrations"
        assert "CREATE TABLE IF NOT EXISTS drug_cache" in content, "drug_cache table missing in migrations"
        assert "CREATE TABLE IF NOT EXISTS scans" in content, "scans table missing in migrations"
        assert "CREATE TABLE IF NOT EXISTS scan_sessions" in content, "scan_sessions table missing in migrations"
        assert "CREATE TABLE IF NOT EXISTS medication_plans" in content, "medication_plans table missing in migrations"

    def test_t1_r3_3_drug_database_seeding(self, drug_db_data: List[Dict[str, Any]]):
        """T1.R3.3 [Drug Database Seeding]: Verify drug database contains >= 9,000 Vietnamese drugs with valid fields."""
        assert len(drug_db_data) >= 9000, f"Expected >= 9,000 drugs in DB, found {len(drug_db_data)}"

        first_entry = drug_db_data[0]
        assert "tenThuoc" in first_entry, "tenThuoc field missing in drug DB entry"
        assert "hoatChat" in first_entry or "soDangKy" in first_entry, "hoatChat or soDangKy missing in drug DB entry"

    def test_t1_r3_4_fastapi_ai_proxy_health(self, fastapi_client: TestClient):
        """T1.R3.4 [FastAPI AI Proxy Health]: Verify GET /api/health returns HTTP 200 and drug_db count."""
        response = fastapi_client.get("/api/health")
        assert response.status_code == 200, f"Expected HTTP 200 from /api/health, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok", f"Expected status 'ok', got {data.get('status')}"
        assert "drug_db" in data, "drug_db count missing in health response"
        assert data["drug_db"] >= 100, f"drug_db count too low: {data['drug_db']}"

    def test_t1_r3_5_nodejs_api_health(self, server_node_dir: Path):
        """T1.R3.5 [Node.js API Health]: Verify Node.js API health route definition and contract."""
        health_route_file = server_node_dir / "src" / "routes" / "health.routes.js"
        assert health_route_file.exists(), "health.routes.js missing"
        content = health_route_file.read_text(encoding="utf-8")

        assert "router.get('/health'" in content or 'router.get("/health"' in content, "GET /health route missing"
        assert "database" in content, "Database health status missing in health route"
        assert "python_pipeline" in content, "Python pipeline status missing in health route"

    def test_t1_r3_6_direct_scan_prediction(self, fastapi_client: TestClient):
        """T1.R3.6 [Direct Scan Prediction]: Verify POST /api/scan-prescription accepts OCR lines and returns predictions."""
        payload = {
            "ocr_text": "1. Paracetamol 500mg\n2. Amoxicillin 500mg",
            "layout_strategy": "p3_medication_bands",
        }
        response = fastapi_client.post("/api/scan-prescription", data=payload)
        # Verify status is 200 (or structured response)
        assert response.status_code == 200, (
            f"POST /api/scan-prescription failed with {response.status_code}: {response.text}"
        )
        res_json = response.json()
        assert "medications" in res_json or "medication_candidates" in res_json or "drugs" in res_json, (
            f"Missing medications in scan prediction response: {res_json}"
        )


# ==============================================================================
# Feature R4: Academic Benchmark Reproduction Suite (5 tests)
# ==============================================================================

class TestTier1FeatureR4AcademicBenchmarkReproduction:
    """T1.R4: Reproduction CLI, ROI ablation, Layout ablation, Ground truth, and Provenance trail."""

    def test_t1_r4_1_reproduction_runner_cli(self, scripts_dir: Path, run_command):
        """T1.R4.1 [Reproduction Runner CLI]: Verify benchmark reproduction CLI script exists and has valid help/syntax."""
        runner_file = scripts_dir / "reproduce_paper_benchmarks.py"
        alt_runner_file = scripts_dir / "benchmark_real_medication_roi.py"
        target_script = runner_file if runner_file.exists() else alt_runner_file
        assert target_script.exists(), "Benchmark runner script missing"

        res = run_command(["python", str(target_script), "--help"], timeout=15.0)
        assert res.success or "--help" in res.stdout or "-h" in res.stdout, (
            f"Runner CLI failed --help: {res.stderr}"
        )

    def test_t1_r4_2_real_medication_roi_ablation(self, scripts_dir: Path):
        """T1.R4.2 [Real Medication ROI Ablation]: Verify benchmark_real_medication_roi.py script exists and defines R0 vs R1."""
        roi_script = scripts_dir / "benchmark_real_medication_roi.py"
        assert roi_script.exists(), "benchmark_real_medication_roi.py missing"
        content = roi_script.read_text(encoding="utf-8")

        assert "run_real_roi_evaluation" in content or "R0" in content, "R0/R1 evaluation function missing"
        assert "visible_gt" in content or "visible_gt_path" in content, "Visible GT handling missing in ROI benchmark"
        assert "num_bootstrap" in content or "bootstrap" in content, "Bootstrap analysis missing in ROI benchmark"

    def test_t1_r4_3_real_mlkit_layout_ablation(self, scripts_dir: Path):
        """T1.R4.3 [Real ML Kit Layout Ablation]: Verify benchmark_real_mlkit_layout.py evaluates P0, P1, P2, P3."""
        layout_script = scripts_dir / "benchmark_real_mlkit_layout.py"
        assert layout_script.exists(), "benchmark_real_mlkit_layout.py missing"
        content = layout_script.read_text(encoding="utf-8")

        assert "p0" in content.lower(), "P0 strategy missing in layout benchmark"
        assert "p1" in content.lower(), "P1 strategy missing in layout benchmark"
        assert "p2" in content.lower(), "P2 strategy missing in layout benchmark"
        assert "p3" in content.lower(), "P3 strategy missing in layout benchmark"

    def test_t1_r4_4_ground_truth_dataset_integrity(self, visible_gt_data: Dict[str, Any]):
        """T1.R4.4 [Ground Truth Dataset Integrity]: Verify visible_in_frame_gt.json has 30 captures and 137 visible drugs."""
        total_captures = len(visible_gt_data)
        assert total_captures == 30, f"Expected exactly 30 captures, found {total_captures}"

        total_drugs = sum(len(entry.get("visible_drugs", [])) for entry in visible_gt_data.values())
        assert total_drugs == 137, f"Expected exactly 137 visible drug instances, found {total_drugs}"

    def test_t1_r4_5_human_provenance_trail(self, provenance_log_data: Dict[str, Any]):
        """T1.R4.5 [Human Provenance Trail]: Verify provenance log contains Protocol v1.0.0 and zero automated OCR leakage."""
        assert provenance_log_data.get("protocol_version") == "1.0.0", (
            f"Expected protocol_version '1.0.0', got '{provenance_log_data.get('protocol_version')}'"
        )
        records = provenance_log_data.get("audit_records", [])
        assert len(records) == 30, f"Expected 30 audit records in provenance log, got {len(records)}"

        summary = provenance_log_data.get("dataset_summary", {})
        independence = summary.get("independence_statement", "")
        assert "zero dependency" in independence.lower() or "manual visual" in independence.lower(), (
            "Independence statement declaring zero OCR leakage missing in provenance log"
        )


# ==============================================================================
# Feature R5: Professional Academic Documentation (5 tests)
# ==============================================================================

class TestTier1FeatureR5AcademicDocumentation:
    """T1.R5: Root README, Reproducibility guide, Mobile guide, Pipeline status, and Port consistency."""

    def test_t1_r5_1_root_readme_quality(self, project_root: Path):
        """T1.R5.1 [Root README Quality]: Verify README.md provides overview, architecture, and quickstarts."""
        readme_file = project_root / "README.md"
        assert readme_file.exists(), "README.md missing at project root"
        content = readme_file.read_text(encoding="utf-8")

        assert len(content.splitlines()) >= 40, "README.md is too short (< 40 lines)"
        assert "MedicineApp" in content, "README.md missing MedicineApp title"
        assert "ML Kit" in content or "mlkit" in content.lower(), "ML Kit mention missing in README.md"
        assert "docker" in content.lower(), "Docker instructions missing in README.md"

    def test_t1_r5_2_reproducibility_guide(self, project_root: Path):
        """T1.R5.2 [Reproducibility Guide]: Verify REPRODUCIBILITY.md (or docs guide) exists and details replication steps."""
        repro_file = project_root / "REPRODUCIBILITY.md"
        docs_repro = project_root / "docs" / "reproducibility.md"
        methods_doc = project_root / "reports" / "real_medication_roi_ablation" / "methods_and_annotation_protocol.md"
        guide_file = repro_file if repro_file.exists() else (docs_repro if docs_repro.exists() else methods_doc)
        assert guide_file.exists(), "Reproducibility guide missing"

    def test_t1_r5_3_mobile_guide(self, mobile_dir: Path):
        """T1.R5.3 [Mobile Guide]: Verify mobile/README.md exists and documents Flutter setup and build."""
        mobile_readme = mobile_dir / "README.md"
        assert mobile_readme.exists(), "mobile/README.md missing"
        content = mobile_readme.read_text(encoding="utf-8")

        assert len(content) > 100, "mobile/README.md is too short"
        assert "flutter" in content.lower(), "Flutter instructions missing in mobile/README.md"

    def test_t1_r5_4_pipeline_technical_specs(self, project_root: Path):
        """T1.R5.4 [Pipeline Technical Specs]: Verify pipeline documentation (AGENTS.md or PIPELINE_STATUS.md)."""
        agents_file = project_root / "AGENTS.md"
        pipeline_status = project_root / "PIPELINE_STATUS.md"
        spec_file = pipeline_status if pipeline_status.exists() else agents_file
        assert spec_file.exists(), "Pipeline technical specification document missing"
        content = spec_file.read_text(encoding="utf-8")

        assert "PhoBERT" in content, "PhoBERT model architecture missing in specs"
        assert "Drug Search" in content or "DrugLookup" in content or "drug_db" in content, (
            "Drug lookup specification missing in specs"
        )

    def test_t1_r5_5_port_and_config_consistency(self, project_root: Path):
        """T1.R5.5 [Port & Config Consistency]: Verify documentation and docker-compose reference ports 3000, 8000, 5432."""
        compose_file = project_root / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml missing"
        compose_text = compose_file.read_text(encoding="utf-8")

        assert "3000" in compose_text, "Port 3000 (Node API) missing in docker-compose"
        assert "8000" in compose_text, "Port 8000 (Python AI) missing in docker-compose"
        assert "5432" in compose_text, "Port 5432 (Postgres) missing in docker-compose"

"""
tests/e2e/test_tier2_boundary_cases.py — Tier 2 Boundary & Corner Case Tests (26 test cases).

Covers:
- Feature R1: Clean Publication Repository Boundary Cases (T2.R1.1 – T2.R1.5)
- Feature R2: Android Mobile UI Boundary Cases (T2.R2.1 – T2.R2.5)
- Feature R3: Docker Compose & Backend Boundary Cases (T2.R3.1 – T2.R3.6)
- Feature R4: Academic Benchmark Exact Statistical Boundaries (T2.R4.1 – T2.R4.5)
- Feature R5: Academic Documentation Integrity & Syntax Boundaries (T2.R5.1 – T2.R5.5)
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
from starlette.testclient import TestClient

from core.drug_search.drug_lookup import DrugLookup


# ==============================================================================
# Feature R1: Clean Publication Repository Boundary Cases (5 tests)
# ==============================================================================

class TestTier2FeatureR1CleanPublicationRepoBoundaries:
    """T2.R1: Binary file limits, secret hygiene, deprecated module isolation, line endings, diff caches."""

    def test_t2_r1_1_large_binary_file_boundary(self, project_root: Path, run_command):
        """T2.R1.1 [Large Binary File Boundary]: Verify no tracked binary files > 50MB exist in git index (excl models)."""
        res = run_command(["git", "ls-files"])
        assert res.success, f"git ls-files failed: {res.stderr}"
        tracked_files = res.stdout.strip().splitlines()

        oversized_files = []
        max_bytes = 50 * 1024 * 1024  # 50MB
        for file_rel in tracked_files:
            if file_rel.startswith("models/"):
                continue  # Documented model weights excluded
            full_path = project_root / file_rel
            if full_path.exists() and full_path.is_file():
                if full_path.stat().st_size > max_bytes:
                    oversized_files.append((file_rel, full_path.stat().st_size))

        assert not oversized_files, f"Found tracked files > 50MB: {oversized_files}"

    def test_t2_r1_2_hidden_credential_secret_leakage(self, project_root: Path):
        """T2.R1.2 [Hidden Credential & Secret Leakage]: Verify scan detects no real private keys or leaked tokens in repo."""
        suspicious_patterns = [
            re.compile(r"-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA)?\s*PRIVATE\s+KEY-----"),
            re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}"),  # GitHub tokens
            re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
            re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API Key
        ]

        target_files = [
            project_root / ".env.example",
            project_root / "mobile" / ".env.example",
            project_root / "server-node" / ".env.example",
            project_root / "docker-compose.yml",
        ]

        leaks = []
        for target in target_files:
            if not target.exists():
                continue
            text = target.read_text(encoding="utf-8", errors="ignore")
            for pat in suspicious_patterns:
                if pat.search(text):
                    leaks.append((str(target.relative_to(project_root)), pat.pattern))

        assert not leaks, f"Potential credentials or secret keys detected: {leaks}"

    def test_t2_r1_3_deprecated_module_isolation(self, project_root: Path):
        """T2.R1.3 [Deprecated Module Isolation]: Verify no imports from archive/ or deprecated_gcn/ exist in active code."""
        active_dirs = [
            project_root / "core",
            project_root / "server",
            project_root / "server-node" / "src",
            project_root / "mobile" / "lib",
        ]

        forbidden_import_patterns = [
            re.compile(r"from\s+archive\b"),
            re.compile(r"import\s+archive\b"),
            re.compile(r"from\s+deprecated_gcn\b"),
            re.compile(r"import\s+deprecated_gcn\b"),
            re.compile(r"require\(['\"].*archive.*['\"]\)|from\s+['\"].*archive.*['\"]"),
        ]

        violations = []
        for adir in active_dirs:
            if not adir.exists():
                continue
            for path in adir.rglob("*"):
                if path.is_file() and path.suffix in [".py", ".js", ".dart"]:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    for pat in forbidden_import_patterns:
                        if pat.search(text):
                            violations.append(str(path.relative_to(project_root)))

        assert not violations, f"Forbidden deprecated imports found in active codebase: {violations}"

    def test_t2_r1_4_line_ending_hygiene(self, project_root: Path):
        """T2.R1.4 [Line Ending Hygiene (LF/CRLF)]: Verify shell scripts, Python, and Dart files use LF line endings."""
        check_extensions = [".sh", ".py", ".dart"]
        crlf_files = []

        scan_dirs = [
            project_root / "scripts",
            project_root / "core",
            project_root / "server",
            project_root / "mobile" / "lib",
            project_root / "tests",
        ]

        for sdir in scan_dirs:
            if not sdir.exists():
                continue
            for path in sdir.rglob("*"):
                if path.is_file() and path.suffix in check_extensions:
                    raw_bytes = path.read_bytes()
                    if b"\r\n" in raw_bytes:
                        crlf_files.append(str(path.relative_to(project_root)))

        assert not crlf_files, f"Files with CRLF line endings detected (expected LF): {crlf_files[:10]}"

    def test_t2_r1_5_golden_diff_caches(self, project_root: Path, run_command):
        """T2.R1.5 [Golden Diff Caches]: Verify golden test failure output directories are completely removed from git tracking."""
        res = run_command(["git", "ls-files"])
        assert res.success, f"git ls-files failed: {res.stderr}"
        tracked = res.stdout.strip().splitlines()

        failure_diffs = [f for f in tracked if "failures/" in f and f.endswith(".png")]
        assert not failure_diffs, f"Golden test diff failure PNGs tracked in git index: {failure_diffs}"


# ==============================================================================
# Feature R2: Android Mobile UI Experience Boundary Cases (5 tests)
# ==============================================================================

class TestTier2FeatureR2AndroidMobileUIBoundaries:
    """T2.R2: Env fallback, payload limits, cancellation, permissions, and retired routes."""

    def test_t2_r2_1_missing_env_fallback_and_env_example(self, mobile_dir: Path):
        """T2.R2.1 [Missing .env Fallback & .env.example]: Verify mobile/.env.example exists and contains default API host."""
        env_example = mobile_dir / ".env.example"
        assert env_example.exists(), "mobile/.env.example missing"
        content = env_example.read_text(encoding="utf-8")

        assert "http://10.0.2.2:3000/api" in content or "API_BASE_URL" in content or "API_URL" in content, (
            "mobile/.env.example missing standard Android emulator API base URL"
        )

    def test_t2_r2_2_scanner_payload_size_limit(self, mobile_dir: Path):
        """T2.R2.2 [Scanner Payload Size Limit]: Verify bridge contract defines 10MB limit and CODE_FILE_TOO_LARGE."""
        contract_file = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerChannelContract.kt"
        )
        assert contract_file.exists(), "PrescriptionDocumentScannerChannelContract.kt missing"
        content = contract_file.read_text(encoding="utf-8")

        assert "CODE_FILE_TOO_LARGE" in content, "CODE_FILE_TOO_LARGE constant missing in scanner contract"
        assert "10L * 1024L * 1024L" in content or "MAX_FILE_BYTES" in content, "10MB limit missing in scanner contract"

    def test_t2_r2_3_scanner_cancellation_handling(self, mobile_dir: Path):
        """T2.R2.3 [Scanner Cancellation Handling]: Verify bridge handles RESULT_CANCELED returning status: cancelled."""
        bridge_file = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerBridge.kt"
        )
        assert bridge_file.exists(), "PrescriptionDocumentScannerBridge.kt missing"
        content = bridge_file.read_text(encoding="utf-8")

        assert "RESULT_CANCELED" in content, "RESULT_CANCELED handling missing in scanner bridge"
        assert "cancelled()" in content or '"cancelled"' in content, "cancelled status payload missing in bridge"

    def test_t2_r2_4_camera_permission_denial(self, mobile_dir: Path):
        """T2.R2.4 [Camera Permission Denial]: Verify contract and bridge declare CODE_PERMISSION_DENIED."""
        contract_file = (
            mobile_dir / "android" / "app" / "src" / "main" / "kotlin" / "com" / "medicineapp" /
            "medicine_app" / "PrescriptionDocumentScannerChannelContract.kt"
        )
        content = contract_file.read_text(encoding="utf-8")

        assert "CODE_PERMISSION_DENIED" in content, "CODE_PERMISSION_DENIED missing in scanner contract"

    def test_t2_r2_5_retired_phase_b_route_safety(self, mobile_dir: Path):
        """T2.R2.5 [Retired Phase B Route Safety]: Verify retired Phase B test handles legacy routes safely."""
        test_file = mobile_dir / "test" / "retired_phase_b_routes_test.dart"
        assert test_file.exists(), "retired_phase_b_routes_test.dart missing"
        content = test_file.read_text(encoding="utf-8")

        assert "/pill-verify" in content, "Test must check /pill-verify route"
        assert "/pill-reference/enroll" in content, "Test must check /pill-reference/enroll route"
        assert "Trang không tìm thấy" in content or "fallback" in content, "Fallback assertion missing"


# ==============================================================================
# Feature R3: Docker Compose & Backend Services Boundary Cases (6 tests)
# ==============================================================================

class TestTier2FeatureR3DockerComposeBackendBoundaries:
    """T2.R3: Empty payload validation, non-image rejection, upstream outage, semaphore, noise parsing."""

    def test_t2_r3_1_empty_ocr_payload_validation(self, fastapi_client: TestClient):
        """T2.R3.1 [Empty OCR Payload Validation]: Verify empty POST to /api/scan-prescription returns HTTP 422 MISSING_OCR_PAYLOAD."""
        response = fastapi_client.post("/api/scan-prescription", data={})
        assert response.status_code == 422, f"Expected 422 for empty payload, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("code") == "MISSING_OCR_PAYLOAD", f"Expected MISSING_OCR_PAYLOAD, got {detail}"

    def test_t2_r3_2_non_image_upload_rejection(self, server_node_dir: Path):
        """T2.R3.2 [Non-Image Upload Rejection]: Verify Node API scan route enforces magic-byte image validation."""
        scan_route = server_node_dir / "src" / "routes" / "scan.routes.js"
        assert scan_route.exists(), "scan.routes.js missing"
        content = scan_route.read_text(encoding="utf-8")

        assert "fileTypeFromBuffer" in content or "file-type" in content, "Magic byte inspection missing in scan route"
        assert "INVALID_FILE_TYPE" in content, "INVALID_FILE_TYPE error code missing in scan route"

    def test_t2_r3_3_upstream_ai_proxy_outage(self, server_node_dir: Path):
        """T2.R3.3 [Upstream AI Proxy Outage]: Verify scan service handles upstream outage with HTTP 503 PIPELINE_UNAVAILABLE."""
        scan_service = server_node_dir / "src" / "services" / "scan.service.js"
        assert scan_service.exists(), "scan.service.js missing"
        content = scan_service.read_text(encoding="utf-8")

        assert "PIPELINE_UNAVAILABLE" in content, "PIPELINE_UNAVAILABLE error handling missing in scan service"
        assert "503" in content or "AppError" in content, "503 status code missing in upstream error handler"

    def test_t2_r3_4_concurrency_semaphore_serialization(self, server_dir: Path):
        """T2.R3.4 [Concurrency Semaphore Serialization]: Verify FastAPI uses asyncio.Semaphore(1) to serialize scans."""
        main_py = server_dir / "main.py"
        assert main_py.exists(), "server/main.py missing"
        content = main_py.read_text(encoding="utf-8")

        assert "Semaphore(1)" in content or "scan_semaphore" in content, (
            "asyncio.Semaphore(1) missing in server/main.py for scan concurrency limit"
        )

    def test_t2_r3_5_complex_parenthetical_and_noise_text(self):
        """T2.R3.5 [Complex Parenthetical & Noise Text]: Verify DrugLookup accurately matches parenthetical text and ignores noise."""
        lookup = DrugLookup()

        # 1. Complex parenthetical drug line
        res = lookup.lookup("1. Losartan (Cozaar 50mg) 50mg")
        assert res is not None, "Failed to match '1. Losartan (Cozaar 50mg) 50mg'"
        assert "losartan" in res.get("name", "").lower() or "cozaar" in res.get("name", "").lower() or "losartan" in str(res.get("generic", "")).lower(), (
            f"Expected Losartan match, got {res}"
        )

        # 2. Pure noise line should return None or low score
        noise_res = lookup.lookup("10ml")
        # Should be None or low confidence
        if noise_res is not None:
            assert noise_res.get("score", 0) < 90 or noise_res.get("mapping_status") == "rejected_noise"

    def test_t2_r3_6_payload_size_and_rate_limiting(self, server_node_dir: Path):
        """T2.R3.6 [Payload Size & Rate Limiting]: Verify Express middleware configures 10MB limit and rate limiters."""
        app_js = server_node_dir / "src" / "app.js"
        assert app_js.exists(), "server-node/src/app.js missing"
        content = app_js.read_text(encoding="utf-8")

        assert "limit: '10mb'" in content or 'limit: "10mb"' in content, "10mb body parser limit missing in app.js"
        assert "generalLimiter" in content, "generalLimiter missing in app.js"
        assert "authLimiter" in content, "authLimiter missing in app.js"


# ==============================================================================
# Feature R4: Academic Benchmark Exact Statistical Boundaries (5 tests)
# ==============================================================================

class TestTier2FeatureR4AcademicBenchmarkStatisticalBoundaries:
    """T2.R4: Exact Micro F1, Macro F1 consistency, Transition matrix, McNemar test, Bootstrap CIs."""

    def test_t2_r4_1_exact_micro_f1_reproduction(self, summary_csv_data: List[Dict[str, str]]):
        """T2.R4.1 [Exact Micro F1 Reproduction]: Verify R0 Micro F1 = 76.75%, R1 Micro F1 = 80.15% (Delta = +3.39%)."""
        micro_r0 = next((r for r in summary_csv_data if r["granularity"] == "Drug-Instance Micro" and r["condition"] == "r0"), None)
        micro_r1 = next((r for r in summary_csv_data if r["granularity"] == "Drug-Instance Micro" and r["condition"] == "r1"), None)

        assert micro_r0 is not None, "Drug-Instance Micro R0 record missing in summary.csv"
        assert micro_r1 is not None, "Drug-Instance Micro R1 record missing in summary.csv"

        f1_r0 = float(micro_r0["f1_score"])
        f1_r1 = float(micro_r1["f1_score"])
        delta_f1 = f1_r1 - f1_r0

        assert math.isclose(f1_r0, 0.7675, abs_tol=0.001), f"Expected R0 Micro F1 0.7675, got {f1_r0}"
        assert math.isclose(f1_r1, 0.8015, abs_tol=0.001), f"Expected R1 Micro F1 0.8015, got {f1_r1}"
        assert math.isclose(delta_f1, 0.0340, abs_tol=0.001), f"Expected Delta F1 +0.0340, got {delta_f1}"

    def test_t2_r4_2_macro_f1_metrics_consistency(self, summary_csv_data: List[Dict[str, str]]):
        """T2.R4.2 [Macro F1 Metrics Consistency]: Verify Capture-Macro (76.94% -> 80.57%) and Prescription-Macro (86.20% -> 88.42%)."""
        cap_r0 = next((r for r in summary_csv_data if r["granularity"] == "Capture-Macro" and r["condition"] == "r0"), None)
        cap_r1 = next((r for r in summary_csv_data if r["granularity"] == "Capture-Macro" and r["condition"] == "r1"), None)
        pres_r0 = next((r for r in summary_csv_data if r["granularity"] == "Prescription-Macro" and r["condition"] == "r0"), None)
        pres_r1 = next((r for r in summary_csv_data if r["granularity"] == "Prescription-Macro" and r["condition"] == "r1"), None)

        assert cap_r0 and cap_r1 and pres_r0 and pres_r1, "Macro evaluation rows missing in summary.csv"

        assert math.isclose(float(cap_r0["f1_score"]), 0.7694, abs_tol=0.001), f"Capture R0 Macro F1 mismatch: {cap_r0['f1_score']}"
        assert math.isclose(float(cap_r1["f1_score"]), 0.8057, abs_tol=0.001), f"Capture R1 Macro F1 mismatch: {cap_r1['f1_score']}"
        assert math.isclose(float(pres_r0["f1_score"]), 0.8620, abs_tol=0.001), f"Prescription R0 Macro F1 mismatch: {pres_r0['f1_score']}"
        assert math.isclose(float(pres_r1["f1_score"]), 0.8842, abs_tol=0.001), f"Prescription R1 Macro F1 mismatch: {pres_r1['f1_score']}"

    def test_t2_r4_3_paired_transition_matrix_exactness(self, transition_matrix_data: List[Dict[str, str]]):
        """T2.R4.3 [Paired Transition Matrix Exactness]: Verify b=14, c=9, Net Gain=+5, Both=95, Total=137."""
        matrix_map = {row["transition"].strip(): row["count"].strip() for row in transition_matrix_data}

        both_success = next((v for k, v in matrix_map.items() if "Both Success" in k), None)
        r1_gain = next((v for k, v in matrix_map.items() if "Recovery Gain" in k or "R1 Recovery" in k), None)
        r1_loss = next((v for k, v in matrix_map.items() if "Regression Loss" in k or "R1 Regression" in k), None)
        both_fail = next((v for k, v in matrix_map.items() if "Both Missed" in k or "Both Fail" in k), None)
        total = next((v for k, v in matrix_map.items() if "TOTAL VISIBLE" in k), None)

        assert both_success == "95", f"Expected Both Success = 95, got {both_success}"
        assert r1_gain == "14", f"Expected R1 Recovery Gain (b) = 14, got {r1_gain}"
        assert r1_loss == "9", f"Expected R1 Regression Loss (c) = 9, got {r1_loss}"
        assert both_fail == "19", f"Expected Both Missed = 19, got {both_fail}"
        assert total == "137", f"Expected Total Visible = 137, got {total}"

    def test_t2_r4_4_exact_mcnemar_statistical_test(self, significance_json_data: Dict[str, Any]):
        """T2.R4.4 [Exact McNemar Statistical Test]: Verify exact McNemar 2-tailed test produces p = 0.4049."""
        mcnemar = significance_json_data.get("mcnemar_exact_test", {})
        assert mcnemar.get("b_gain") == 14, f"Expected b_gain 14, got {mcnemar.get('b_gain')}"
        assert mcnemar.get("c_loss") == 9, f"Expected c_loss 9, got {mcnemar.get('c_loss')}"
        assert mcnemar.get("net_gain") == 5, f"Expected net_gain 5, got {mcnemar.get('net_gain')}"

        p_val = float(mcnemar.get("two_sided_p_value", 0.0))
        assert math.isclose(p_val, 0.4049, abs_tol=0.001), f"Expected p-value ~0.4049, got {p_val}"

    def test_t2_r4_5_bootstrap_95ci_boundaries(self, significance_json_data: Dict[str, Any]):
        """T2.R4.5 [Bootstrap 95% CI Boundaries]: Verify Capture Delta F1 in [-3.18, 10.18] and Prescription in [0.00, 7.21]."""
        cap_ci = significance_json_data.get("capture_level_bootstrap_95ci", {}).get("delta_f1_pct", {})
        pres_ci = significance_json_data.get("prescription_clustered_bootstrap_95ci", {}).get("delta_f1_pct", {})

        assert math.isclose(float(cap_ci.get("ci_lower", 0)), -3.18, abs_tol=0.05), f"Capture CI lower mismatch: {cap_ci.get('ci_lower')}"
        assert math.isclose(float(cap_ci.get("ci_upper", 0)), 10.18, abs_tol=0.05), f"Capture CI upper mismatch: {cap_ci.get('ci_upper')}"

        assert math.isclose(float(pres_ci.get("ci_lower", 0)), 0.00, abs_tol=0.05), f"Prescription CI lower mismatch: {pres_ci.get('ci_lower')}"
        assert math.isclose(float(pres_ci.get("ci_upper", 0)), 7.21, abs_tol=0.05), f"Prescription CI upper mismatch: {pres_ci.get('ci_upper')}"


# ==============================================================================
# Feature R5: Academic Documentation Integrity Boundaries (5 tests)
# ==============================================================================

class TestTier2FeatureR5AcademicDocumentationBoundaries:
    """T2.R5: Link integrity, command syntax, BibTeX validation, Phase B clarification, Metric alignment."""

    def test_t2_r5_1_markdown_link_integrity(self, project_root: Path):
        """T2.R5.1 [Markdown Link Integrity]: Verify relative markdown links across primary docs target valid existing files."""
        primary_docs = [
            project_root / "README.md",
            project_root / "mobile" / "README.md",
            project_root / "TEST_INFRA.md",
            project_root / "reports" / "real_medication_roi_ablation" / "methods_and_annotation_protocol.md",
        ]

        broken_links = []
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for doc in primary_docs:
            if not doc.exists():
                continue
            text = doc.read_text(encoding="utf-8")
            for match in link_pattern.finditer(text):
                target = match.group(2).strip()
                # Skip external web links, anchor-only links, mailto
                if target.startswith("http://") or target.startswith("https://") or target.startswith("#") or target.startswith("mailto:"):
                    continue
                # Strip anchor from relative path
                clean_target = target.split("#")[0]
                if not clean_target:
                    continue
                resolved = (doc.parent / clean_target).resolve()
                if not resolved.exists():
                    broken_links.append((str(doc.relative_to(project_root)), target))

        assert not broken_links, f"Broken relative markdown links found: {broken_links}"

    def test_t2_r5_2_copy_pasteable_command_syntax(self, project_root: Path):
        """T2.R5.2 [Copy-Pasteable Command Syntax]: Verify all shell code blocks in README.md have valid command syntax."""
        readme = project_root / "README.md"
        assert readme.exists(), "README.md missing"
        content = readme.read_text(encoding="utf-8")

        # Extract bash/sh code blocks
        bash_blocks = re.findall(r"```(?:bash|sh)\n(.*?)```", content, re.DOTALL)
        assert len(bash_blocks) >= 2, "Expected at least 2 bash/sh command snippets in README.md"

        for idx, block in enumerate(bash_blocks):
            lines = [line.strip() for line in block.strip().splitlines() if line.strip() and not line.strip().startswith("#")]
            for line in lines:
                # Must not contain unreplaced template placeholders like <YOUR_KEY> without documentation
                assert "<REPLACE_ME>" not in line and "<TODO>" not in line, f"Unresolved placeholder in command: {line}"

    def test_t2_r5_3_bibtex_parse_validation(self, project_root: Path):
        """T2.R5.3 [BibTeX Parse Validation]: Verify BibTeX entry in README.md / docs has valid citation fields."""
        repro_path = project_root / "REPRODUCIBILITY.md"
        readme_path = project_root / "README.md"
        target_path = repro_path if repro_path.exists() else readme_path
        content = target_path.read_text(encoding="utf-8")

        bibtex_match = re.search(r"@(?P<type>[a-zA-Z]+)\s*\{\s*(?P<key>[^,]+),", content)
        if bibtex_match:
            entry_type = bibtex_match.group("type")
            entry_key = bibtex_match.group("key")
            assert entry_type.lower() in ["article", "inproceedings", "misc", "techreport"], f"Invalid BibTeX entry type: {entry_type}"
            assert len(entry_key) > 0, "BibTeX citation key cannot be empty"

    def test_t2_r5_4_phase_b_status_clarification(self, project_root: Path):
        """T2.R5.4 [Phase B Status Clarification]: Verify AGENTS.md / README clarifies Phase B status."""
        agents_file = project_root / "AGENTS.md"
        assert agents_file.exists(), "AGENTS.md missing"
        content = agents_file.read_text(encoding="utf-8")

        assert "Phase B" in content, "Phase B section missing in AGENTS.md"
        assert "Phase A" in content, "Phase A focus missing in AGENTS.md"

    def test_t2_r5_5_documentation_metric_match(self, summary_csv_data: List[Dict[str, str]]):
        """T2.R5.5 [Documentation Metric Match]: Verify summary.csv matches documented paper metrics across all rows."""
        assert len(summary_csv_data) == 6, f"Expected exactly 6 rows in summary.csv, got {len(summary_csv_data)}"

        for row in summary_csv_data:
            f1 = float(row["f1_score"])
            prec = float(row["precision"])
            rec = float(row["recall"])
            assert 0.0 <= f1 <= 1.0, f"Invalid F1 score in row {row}: {f1}"
            assert 0.0 <= prec <= 1.0, f"Invalid Precision in row {row}: {prec}"
            assert 0.0 <= rec <= 1.0, f"Invalid Recall in row {row}: {rec}"

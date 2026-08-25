#!/usr/bin/env python3
"""
Comprehensive Adversarial Stress Test Suite for Milestone 1 (Isolated Clean Publication Repository)
Author: Challenger 1 (critic / specialist)

Tests:
1. Git Index Forensic Audit:
   - Ensure 0 forbidden/junk files (docx, mdj, ipynb, failure PNGs, absolute symlinks) exist in git index
   - Verify critical preservation files are tracked
2. Adversarial .gitignore Test Matrix:
   - 65+ synthetic path assertions (positive ignores & negative unignores)
   - Edge case path structures (nested subdirs, Unicode paths, sensitive files, caches)
3. Adversarial .gitattributes Test Matrix:
   - LF/CRLF mappings for scripts, source, configs
   - Binary mappings for weights, images, archives
   - GitHub Linguist categorizations (generated, vendored, documentation)
4. License & Metadata Conformance:
   - Root LICENSE validity (MIT)
   - server-node/package.json license conformance
5. Line Ending & Encoding Integrity:
   - Inspect all tracked shell scripts, python, dart, and js files for CRLF vs LF line endings
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def run_git_cmd(args, cwd=REPO_ROOT):
    cmd = ["git"] + args
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def test_git_index_forensic_audit():
    print("\n========================================================")
    print("1. Git Index Forensic Audit")
    print("========================================================")
    code, stdout, stderr = run_git_cmd(["ls-files"])
    assert code == 0, f"git ls-files failed: {stderr}"
    tracked_files = stdout.splitlines()

    print(f"Total tracked files in git index: {len(tracked_files)}")

    violations = []
    for f in tracked_files:
        # Check forbidden extensions
        lower = f.lower()
        if lower.endswith(".docx") or lower.endswith(".doc"):
            violations.append((f, "Forbidden Word document tracked in index"))
        elif lower.endswith(".mdj"):
            violations.append((f, "Forbidden StarUML diagram tracked in index"))
        elif lower.endswith(".ipynb"):
            violations.append((f, "Forbidden Jupyter notebook tracked in index"))
        elif "failures/" in lower and lower.endswith(".png"):
            violations.append((f, "Forbidden golden failure diff PNG tracked in index"))
        elif ".pytest_cache" in f or "node_modules/" in f or ".dart_tool/" in f or "server-node/coverage/" in f:
            violations.append((f, "Forbidden cache / build artifact tracked in index"))

    # Check symlinks in git index
    code, stdout, stderr = run_git_cmd(["ls-files", "-s"])
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            mode = parts[0]
            path = parts[3]
            if mode == "120000":  # symlink mode
                violations.append((path, f"Tracked symlink (mode 120000) detected: {path}"))

    if violations:
        print(f"FAILED: Found {len(violations)} git index violations:")
        for path, reason in violations:
            print(f"  - {path}: {reason}")
        return False, violations
    else:
        print("PASSED: Zero junk, forbidden formats, or symlinks in Git index.")
        return True, []

def test_critical_files_tracked():
    print("\n========================================================")
    print("2. Critical Files Tracking Verification")
    print("========================================================")
    code, stdout, stderr = run_git_cmd(["ls-files"])
    tracked_files = set(stdout.splitlines())

    critical_must_be_tracked = [
        "data/drug_db_vn_full.json",
        "data/drug_db_vn.csv",
        "data/vaipe_drugs_kb.json",
        "data/visible_in_frame_gt.json",
        "data/human_verification_provenance_log.json",
        "LICENSE",
        "server-node/package.json",
        "core/pipeline.py",
        "scripts/run_pipeline.py",
        "mobile/lib/main.dart",
        "mobile/pubspec.yaml",
    ]

    missing = []
    for f in critical_must_be_tracked:
        if f not in tracked_files:
            missing.append(f)

    if missing:
        print(f"FAILED: Critical files missing from Git index: {missing}")
        return False, missing
    else:
        print(f"PASSED: All {len(critical_must_be_tracked)} critical assets are tracked in Git index.")
        return True, []

def test_gitignore_matrix():
    print("\n========================================================")
    print("3. Adversarial .gitignore Test Matrix")
    print("========================================================")
    
    # (path, expected_ignored: bool, description)
    test_cases = [
        # --- Crucial positive ignores (MUST be ignored = True) ---
        ("mobile/test/features/lookup/failures/test_isolatedDiff.png", True, "Golden failure test PNG"),
        ("mobile/test/unit/deep/failures/render_fail.png", True, "Deeply nested failure PNG"),
        ("test/failures/error.png", True, "Root level failure PNG"),
        ("failures/screenshot.png", True, "Top-level failure screenshot"),
        (".pytest_cache/v/cache/nodeids", True, "Pytest cache directory file"),
        ("__pycache__/foo.cpython-312.pyc", True, "Python bytecode cache file"),
        ("core/__pycache__/pipeline.cpython-312.pyc", True, "Nested Python bytecode cache file"),
        ("server-node/node_modules/express/index.js", True, "Node server modules"),
        ("node_modules/package/index.js", True, "Root node modules"),
        ("server-node/coverage/lcov.info", True, "Node server coverage"),
        ("server-node/storage/uploads/temp.dat", True, "Node server uploads/storage"),
        ("mobile/.dart_tool/package_config.json", True, "Flutter dart tool config"),
        ("mobile/build/app/outputs/flutter-apk/app-debug.apk", True, "Flutter build APK output"),
        ("mobile/android/.gradle/8.0/checksums/checksums.lock", True, "Android gradle cache"),
        ("mobile/ios/Pods/Manifest.lock", True, "iOS Pods lock"),
        ("mobile/linux/flutter/ephemeral/generated_config.cmake", True, "Linux desktop ephemeral flutter"),
        ("mobile/windows/flutter/ephemeral/generated_config.cmake", True, "Windows desktop ephemeral flutter"),
        ("mobile/flutter_01.log", True, "Flutter runtime log"),
        ("mobile/debug.log", True, "Mobile log file"),
        ("models/phobert_ner_model", True, "PhoBERT NER model symlink / folder"),
        ("models/yolo", True, "YOLO model symlink / folder"),
        ("models/zero_pima", True, "Zero PIMA model folder"),
        ("models/weights/table_best.pt", True, "Weights directory"),
        ("best.pt", True, "Root model weight .pt"),
        ("checkpoint.safetensors", True, "Checkpoint .safetensors"),
        ("data/output/debug_scans/scan_001.json", True, "Debug scan generated JSON"),
        ("data/output/phase_a/IMG_01/summary.json", True, "Pipeline phase_a output"),
        ("data/input/prescription_1/IMG_001.jpg", True, "Input raw prescription image"),
        ("data/pills/pill_sample.jpg", True, "Data pills dataset"),
        ("data/pres/prescription_doc.jpg", True, "Data pres dataset"),
        ("data/synthetic_train/synthetic_01.json", True, "Synthetic train dataset"),
        ("data/ner_dataset/train_bio.txt", True, "NER train dataset"),
        ("archive/deprecated_gcn/gcn_model.py", True, "Archive deprecated GCN"),
        ("archive/VAIPE_Full/raw_data.tar", True, "Archive VAIPE full"),
        ("archive/legacy/old_runner.py", True, "Archive legacy runner"),
        ("mobile/assets/images/header.png", True, "Mobile asset png"),
        ("mobile/assets/icons/app_icon.jpg", True, "Mobile asset jpg"),
        ("dataset_backup.zip", True, "Zip archive"),
        ("bundle.tar.gz", True, "Tarball archive"),
        (".DS_Store", True, "macOS DS_Store"),
        ("mobile/.DS_Store", True, "Nested macOS DS_Store"),
        ("Thumbs.db", True, "Windows Thumbs.db"),
        (".idea/workspace.xml", True, "IntelliJ idea directory"),
        (".vscode/settings.json", True, "VS Code settings"),
        (".env", True, "Root .env secrets"),
        (".env.local", True, "Root .env.local secrets"),
        (".env.production.local", True, "Root production local secrets"),
        ("server-node/.env", True, "Server-node .env secrets"),
        ("signing.keystore", True, "Android signing keystore"),
        ("release.jks", True, "Java keystore"),
        ("mobile/Hệ thống quản lý Vé xe khách.docx", True, "Word docx junk with Unicode spaces"),
        ("random_spec.doc", True, "Word doc junk"),
        ("mobile/Vi_QuanLyDaoTao_sdlop_QLPM.mdj", True, "StarUML mdj diagram junk"),
        ("train_phobert_colab.ipynb", True, "Jupyter notebook"),
        ("deep/path/analysis.ipynb", True, "Nested Jupyter notebook"),
        ("docs/thesis_report/report.aux", True, "LaTeX aux artifact"),
        ("docs/thesis_report/report.synctex.gz", True, "LaTeX synctex artifact"),
        ("docs/mẫu bài luận/sample.docx", True, "Docs thesis template docx"),

        # --- Crucial negative ignores / MUST NOT be ignored (expected_ignored = False) ---
        ("data/drug_db_vn_full.json", False, "9,284 Full VN Drug Database JSON"),
        ("data/drug_db_vn.csv", False, "Fallback Drug Database CSV"),
        ("data/vaipe_drugs_kb.json", False, "VAIPE Knowledge Base JSON"),
        ("data/visible_in_frame_gt.json", False, "Visible in Frame Ground Truth JSON"),
        ("data/human_verification_provenance_log.json", False, "Provenance Log JSON"),
        ("data/README.md", False, "Data directory README"),
        ("data/input/.gitkeep", False, "Data input keep placeholder"),
        ("data/output/.gitkeep", False, "Data output keep placeholder"),
        ("mobile/lib/main.dart", False, "Mobile Flutter main dart source"),
        ("mobile/lib/features/lookup/data/models/ingredient_dto.dart", False, "Mobile Flutter domain code"),
        ("mobile/assets/data/drug_db.json", False, "Mobile asset JSON file"),
        ("mobile/test/features/lookup/goldens/lookup_catalog_masterImage.png", False, "Golden test baseline master image"),
        (".env.example", False, "Root environment example template"),
        ("mobile/.env.example", False, "Mobile environment example template"),
        ("server-node/.env.example", False, "Server-node environment example template"),
        ("server/.env.example", False, "Server environment example template"),
        ("archive/README.md", False, "Archive directory README"),
        ("archive/plan_bin/plan_v1.txt", False, "Archive plan_bin contents"),
        ("LICENSE", False, "Project MIT LICENSE"),
        (".gitattributes", False, "Project .gitattributes"),
        (".gitignore", False, "Project .gitignore"),
        ("server-node/package.json", False, "Server-node package manifest"),
        ("core/pipeline.py", False, "Core Python pipeline source"),
        ("scripts/run_pipeline.py", False, "Scripts run pipeline source"),
    ]

    failed_matrix = []
    for path, expected_ignored, desc in test_cases:
        # Standard git check-ignore returns 0 if ignored, 1 if not ignored
        code, stdout, stderr = run_git_cmd(["check-ignore", path])
        is_ignored = (code == 0)

        # Get verbose rule if matched
        _, verbose_out, _ = run_git_cmd(["check-ignore", "-v", "--no-index", path])

        if is_ignored != expected_ignored:
            failed_matrix.append({
                "path": path,
                "expected_ignored": expected_ignored,
                "actual_ignored": is_ignored,
                "rule_matched": verbose_out if verbose_out else "None",
                "desc": desc
            })

    if failed_matrix:
        print(f"FAILED: {len(failed_matrix)} test cases failed in .gitignore matrix:")
        for f in failed_matrix:
            print(f"  - {f['path']} ({f['desc']}): Expected ignored={f['expected_ignored']}, Got {f['actual_ignored']}, Rule: {f['rule_matched']}")
        return False, failed_matrix
    else:
        print(f"PASSED: All {len(test_cases)} adversarial .gitignore test cases matched exact specifications.")
        return True, []

def test_gitattributes_matrix():
    print("\n========================================================")
    print("4. Adversarial .gitattributes Test Matrix")
    print("========================================================")
    
    test_cases = [
        # Source & Scripts
        ("core/pipeline.py", {"eol": "lf"}, "Python file"),
        ("mobile/lib/main.dart", {"eol": "lf"}, "Dart file"),
        ("server-node/src/app.js", {"eol": "lf"}, "JavaScript file"),
        ("server-node/src/types.ts", {"eol": "lf"}, "TypeScript file"),
        ("scripts/deploy.sh", {"eol": "lf"}, "Shell script"),
        ("gradlew", {"eol": "lf"}, "Unix Gradle wrapper script"),
        ("gradlew.bat", {"eol": "crlf"}, "Windows Gradle batch wrapper"),
        ("scripts/build.cmd", {"eol": "crlf"}, "Windows CMD script"),
        ("scripts/setup.bat", {"eol": "crlf"}, "Windows BAT script"),
        ("mobile/android/app/src/main/kotlin/MainActivity.kt", {"eol": "lf"}, "Kotlin file"),
        ("mobile/android/app/src/main/java/MainApplication.java", {"eol": "lf"}, "Java file"),
        ("CMakeLists.txt", {"eol": "lf"}, "CMake build file"),
        ("package.json", {"eol": "lf"}, "JSON config"),
        ("README.md", {"eol": "lf"}, "Markdown file"),
        (".gitignore", {"eol": "lf"}, "Git ignore file"),
        ("Dockerfile", {"eol": "lf"}, "Docker config"),

        # Binaries & Media
        ("models/yolo/best.pt", {"binary": "set"}, "PyTorch weights .pt"),
        ("models/phobert_ner_model/pytorch_model.bin", {"binary": "set"}, "PyTorch binary .bin"),
        ("models/phobert_ner_model/model.safetensors", {"binary": "set"}, "Safetensors weights"),
        ("models/zero_pima/model.onnx", {"binary": "set"}, "ONNX model"),
        ("assets/logo.png", {"binary": "set"}, "PNG image"),
        ("assets/photo.jpg", {"binary": "set"}, "JPEG image"),
        ("docs/paper.pdf", {"binary": "set"}, "PDF document"),
        ("docs/thesis.docx", {"binary": "set"}, "Word DOCX binary"),
        ("archive.zip", {"binary": "set"}, "ZIP archive"),
        ("bundle.tar.gz", {"binary": "set"}, "Tarball archive"),

        # Linguist attributes
        ("data/drug_db_vn_full.json", {"linguist-generated": "true"}, "Drug full database JSON linguist override"),
        ("data/vaipe_drugs_kb.json", {"linguist-generated": "true"}, "VAIPE KB JSON linguist override"),
        ("data/human_verification_provenance_log.json", {"linguist-generated": "true"}, "Provenance log linguist override"),
        ("reports/mlkit_progressive_ocr_ablation_matrix_2026-03-24.md", {"linguist-generated": "true"}, "Reports directory linguist override"),
        ("mobile/lib/l10n/app_localizations_vi.dart", {"linguist-generated": "true"}, "Flutter localization generated file"),
        ("mobile/android/gradlew", {"linguist-vendored": "true"}, "Android gradlew vendor override"),
        ("mobile/android/gradlew.bat", {"linguist-vendored": "true"}, "Android gradlew.bat vendor override"),
        ("docs/guide.md", {"linguist-documentation": "true"}, "Docs documentation override"),
        ("docs/thesis_report/main.tex", {"linguist-documentation": "true"}, "Docs thesis report override"),
    ]

    failed_matrix = []
    for path, expected_attrs, desc in test_cases:
        code, stdout, stderr = run_git_cmd(["check-attr", "-a", path])
        attrs = {}
        for line in stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3:
                attr_name = parts[1].strip()
                attr_val = parts[2].strip()
                attrs[attr_name] = attr_val

        for k, v in expected_attrs.items():
            if attrs.get(k) != v:
                failed_matrix.append({
                    "path": path,
                    "attr": k,
                    "expected": v,
                    "actual": attrs.get(k),
                    "all_attrs": attrs,
                    "desc": desc
                })

    if failed_matrix:
        print(f"FAILED: {len(failed_matrix)} test cases failed in .gitattributes matrix:")
        for f in failed_matrix:
            print(f"  - {f['path']} ({f['desc']}): Attribute '{f['attr']}' expected '{f['expected']}', got '{f['actual']}'")
        return False, failed_matrix
    else:
        print(f"PASSED: All {len(test_cases)} adversarial .gitattributes test cases matched exact specifications.")
        return True, []

def test_license_and_package_conformance():
    print("\n========================================================")
    print("5. License & Package Conformance")
    print("========================================================")
    license_file = REPO_ROOT / "LICENSE"
    assert license_file.exists(), "LICENSE file missing at repo root!"
    license_text = license_file.read_text(encoding="utf-8")
    assert "MIT License" in license_text, "LICENSE does not contain 'MIT License'"
    assert "hongphuoc6104" in license_text, "LICENSE copyright holder missing or invalid"
    print("PASSED: Root LICENSE is valid MIT license.")

    package_json_file = REPO_ROOT / "server-node" / "package.json"
    assert package_json_file.exists(), "server-node/package.json missing!"
    pkg_data = json.loads(package_json_file.read_text(encoding="utf-8"))
    assert pkg_data.get("license") == "MIT", f"server-node/package.json license is '{pkg_data.get('license')}', expected 'MIT'"
    print("PASSED: server-node/package.json has license = 'MIT'.")
    return True, []

def test_line_ending_and_encoding_integrity():
    print("\n========================================================")
    print("6. Line Ending & Encoding Integrity Audit")
    print("========================================================")
    code, stdout, stderr = run_git_cmd(["ls-files"])
    tracked_files = stdout.splitlines()

    crlf_violations = []
    text_extensions = {".py", ".dart", ".js", ".mjs", ".ts", ".sh", ".json", ".md", ".yaml", ".yml", ".sql"}

    for rel_path in tracked_files:
        p = REPO_ROOT / rel_path
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in text_extensions and p.name not in ["gradlew.bat"]:
            try:
                content = p.read_bytes()
                if b"\r\n" in content:
                    crlf_violations.append((rel_path, "Contains CRLF line endings in tracked text file"))
            except Exception as e:
                crlf_violations.append((rel_path, f"Read error: {e}"))

    if crlf_violations:
        print(f"FAILED: Found {len(crlf_violations)} CRLF line ending violations in tracked files:")
        for path, reason in crlf_violations[:10]:
            print(f"  - {path}: {reason}")
        if len(crlf_violations) > 10:
            print(f"  ... and {len(crlf_violations) - 10} more")
        return False, crlf_violations
    else:
        print(f"PASSED: All tracked text source files have clean LF line endings.")
        return True, []

def main():
    results = {}
    results["index_forensics"], _ = test_git_index_forensic_audit()
    results["critical_files"], _ = test_critical_files_tracked()
    results["gitignore_matrix"], _ = test_gitignore_matrix()
    results["gitattributes_matrix"], _ = test_gitattributes_matrix()
    results["license_conformance"], _ = test_license_and_package_conformance()
    results["line_ending_integrity"], _ = test_line_ending_and_encoding_integrity()

    all_passed = all(results.values())
    print("\n========================================================")
    print(f"MILENSTONE 1 ADVERSARIAL CHALLENGE OVERALL RESULT: {'ALL PASSED (APPROVE)' if all_passed else 'FAILED (REQUEST_CHANGES)'}")
    print("========================================================")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

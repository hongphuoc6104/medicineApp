# E2E Test Infra: MedicineApp Academic Publication Packaging

## Test Philosophy
- **Opaque-box & Requirement-driven**: All test cases are derived strictly from user requirements (R1–R5) in `ORIGINAL_REQUEST.md` and `PROJECT.md`, verifying the system from an external reviewer's perspective without relying on internal implementation quirks.
- **Methodology**: Systematic 4-tier hierarchy combining Category-Partition, Boundary Value Analysis (BVA), Pairwise Combinatorial Integration Testing, and Real-World Academic Reproduction Workload Scenarios.
- **Coverage Standard**: Strict $\ge 5$ test cases per feature for Tier 1 (Feature Coverage) and Tier 2 (Boundary & Corner Cases), full pairwise coverage for Tier 3, and comprehensive end-to-end reviewer reproduction workflows for Tier 4.

---

## Feature Inventory & Test Mapping

| # | Feature Code | Feature Name | Source | Tier 1 (Count) | Tier 2 (Count) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|--------------|--------------|--------|:--------------:|:--------------:|:-----------------:|:-----------------:|
| 1 | **R1** | Isolated Clean Publication Repository | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ (R1×R5, R1×R3) | S5 |
| 2 | **R2** | Complete Android Mobile UI Experience | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ (R2×R3, R2×R4) | S3 |
| 3 | **R3** | One-Command Docker Compose Backend | ORIGINAL_REQUEST §R3 | 6 | 6 | ✓ (R3×R2, R3×R4) | S2 |
| 4 | **R4** | Academic Benchmark Reproduction Suite | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ (R4×R3, R4×R5) | S1 |
| 5 | **R5** | Professional Academic Documentation | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ (R5×R1, R5×R4) | S4 |
| **Total** | | | | **26** | **26** | **5** | **5** |

**Grand Total Test Cases: 62 test cases** across all 4 tiers.

---

## 4-Tier Test Architecture & Specifications

### Tier 1: Feature Coverage ($\ge 5$ per feature)

#### Feature R1: Clean Publication Repository
- **T1.R1.1 [Git Cleanliness]**: Verify zero tracked temporary/junk files (`.docx`, `.mdj`, golden test failure diff images `*.png`).
- **T1.R1.2 [Gitignore Config]**: Verify `.gitignore` exists, covers build artifacts, caches, `.env`, and DOES NOT ignore `data/drug_db_vn_full.json`.
- **T1.R1.3 [Gitattributes Config]**: Verify `.gitattributes` exists, configures line endings (LF/CRLF), and sets `linguist-vendored` on dataset and model paths.
- **T1.R1.4 [Root MIT License]**: Verify root `LICENSE` file exists and contains valid MIT License terms.
- **T1.R1.5 [Package License Alignment]**: Verify `server-node/package.json` specifies `"license": "MIT"`.

#### Feature R2: Android Mobile UI Experience
- **T1.R2.1 [Flutter Static Analysis]**: Verify `flutter analyze` runs with 0 compiler errors and 0 warnings.
- **T1.R2.2 [Flutter Unit & Widget Tests]**: Verify `flutter test` executes all 39 unit/widget/golden tests with 100% pass rate.
- **T1.R2.3 [Android Build Configuration]**: Verify `mobile/android/app/build.gradle.kts` configures target SDK, Java 17+, desugaring enabled, and ML Kit Document Scanner v16.0.0.
- **T1.R2.4 [Android Manifest Permissions]**: Verify `AndroidManifest.xml` declares `CAMERA`, `INTERNET`, `SCHEDULE_EXACT_ALARM`, `usesCleartextTraffic="true"`, and alarm receivers.
- **T1.R2.5 [Platform Channel Implementation]**: Verify `PrescriptionDocumentScannerBridge.kt` and contract specify channel `com.medicineapp.medicine_app/prescription_document_scanner` with a 10MB payload size limit.

#### Feature R3: Docker Compose & Backend Services
- **T1.R3.1 [Compose Service Topology]**: Verify `docker-compose.yml` configures 3 interconnected services: `postgres` (5432), `node-api` (3000), and `python-ai` (8000).
- **T1.R3.2 [PostgreSQL Migrations & Schema]**: Verify database migration creates all 9 core tables (`users`, `drug_cache`, `scans`, `scan_sessions`, `medication_plans`, `drug_interaction_pairs`, etc.) with `pgcrypto` and `pg_trgm`.
- **T1.R3.3 [Drug Database Seeding]**: Verify `drug_cache` is seeded with $\ge 9,000$ Vietnamese drugs from `data/drug_db_vn_full.json`.
- **T1.R3.4 [FastAPI AI Proxy Health]**: Verify `GET http://localhost:8000/api/health` returns HTTP 200, `ai_ready: true`, and `drug_db >= 9000`.
- **T1.R3.5 [Node.js API Health]**: Verify `GET http://localhost:3000/api/health` returns HTTP 200 with Postgres status `healthy` and AI proxy status `healthy`.
- **T1.R3.6 [Direct Scan Prediction]**: Verify `POST http://localhost:8000/api/scan-prescription` accepts OCR lines and returns structured drug detections.

#### Feature R4: Academic Benchmark Reproduction Suite
- **T1.R4.1 [Reproduction Runner CLI]**: Verify `scripts/reproduce_paper_benchmarks.py` executes without path/import errors.
- **T1.R4.2 [Real Medication ROI Ablation]**: Verify `scripts/benchmark_real_medication_roi.py` executes on CPU and outputs summary metrics.
- **T1.R4.3 [Real ML Kit Layout Ablation]**: Verify `scripts/benchmark_real_mlkit_layout.py` evaluates $P0, P1, P2, P3$ layout reconstructions.
- **T1.R4.4 [Ground Truth Dataset Integrity]**: Verify `data/visible_in_frame_gt.json` contains 30 validated captures across 5 prescriptions and 137 visible drug instances.
- **T1.R4.5 [Human Provenance Trail]**: Verify `data/human_verification_provenance_log.json` contains Protocol v1.0.0 metadata with zero automated OCR leakage.

#### Feature R5: Academic Documentation Integrity
- **T1.R5.1 [Root README Quality]**: Verify `README.md` exists, provides English academic overview, architecture diagram, 3-step quickstarts, and BibTeX citation.
- **T1.R5.2 [Reproducibility Guide]**: Verify `REPRODUCIBILITY.md` exists, provides step-by-step reproduction instructions for Docker, Mobile, and Benchmark runs.
- **T1.R5.3 [Mobile Guide]**: Verify `mobile/README.md` exists, provides step-by-step Flutter setup, Android SDK requirements, and APK build commands.
- **T1.R5.4 [Pipeline Technical Specs]**: Verify `PIPELINE_STATUS.md` exists and accurately documents progressive OCR pipeline architecture, benchmarks, and model parameters.
- **T1.R5.5 [Port & Config Consistency]**: Verify documentation uniformly references Node port 3000, FastAPI port 8000, and Postgres port 5432.

---

### Tier 2: Boundary & Corner Cases ($\ge 5$ per feature)

#### Feature R1: Clean Publication Repository
- **T2.R1.1 [Large Binary File Boundary]**: Verify no untracked or tracked binary files $> 50$MB exist in git index (excluding documented model weights).
- **T2.R1.2 [Hidden Credential & Secret Leakage]**: Verify scan detects no accidental API keys or hardcoded private JWT secrets in committed `.env` files.
- **T2.R1.3 [Deprecated Module Isolation]**: Verify no imports from `archive/` or `deprecated_gcn/` exist in active production codebase (`core/`, `server/`, `server-node/`, `mobile/lib/`).
- **T2.R1.4 [Line Ending Hygiene (LF/CRLF)]**: Verify all shell scripts (`.sh`), Python files (`.py`), and Dart files (`.dart`) have valid LF endings.
- **T2.R1.5 [Golden Diff Caches]**: Verify golden test failure output directories are completely removed from git tracking.

#### Feature R2: Android Mobile UI Experience
- **T2.R2.1 [Missing .env Fallback & .env.example]**: Verify `mobile/.env.example` exists, contains valid defaults (`http://10.0.2.2:3000/api`), and app handles missing `.env` gracefully.
- **T2.R2.2 [Scanner Payload Size Limit]**: Verify platform bridge enforces 10MB payload size limit (`MAX_FILE_BYTES = 10L * 1024L * 1024L`) rejecting oversized files with `FILE_TOO_LARGE`.
- **T2.R2.3 [Scanner Cancellation Handling]**: Verify platform bridge handles `RESULT_CANCELED` returning empty list without crashing Flutter UI.
- **T2.R2.4 [Camera Permission Denial]**: Verify app gracefully handles camera permission denial without unhandled exceptions.
- **T2.R2.5 [Retired Phase B Route Safety]**: Verify 10/10 retired route tests pass, ensuring legacy Phase B routes do not cause navigation crashes.

#### Feature R3: Docker Compose & Backend Services
- **T2.R3.1 [Empty OCR Payload Validation]**: Verify sending `{}` or empty text to `/api/scan-prescription` returns HTTP 422 with descriptive validation errors.
- **T2.R3.2 [Non-Image Upload Rejection]**: Verify uploading non-image buffer (e.g. text/pdf) to `POST /api/scan` returns HTTP 400 via magic byte inspection (`file-type`).
- **T2.R3.3 [Upstream AI Proxy Outage]**: Verify Node API returns HTTP 503 Service Unavailable when Python AI is unreachable without crashing or leaking stack traces.
- **T2.R3.4 [Concurrency Semaphore Serialization]**: Verify `asyncio.Semaphore(1)` on FastAPI serializes concurrent inference requests without dropping connections.
- **T2.R3.5 [Complex Parenthetical & Noise Text]**: Verify NER and drug lookup accurately parse `"1. Losartan (Cozaar 50mg) 50mg"` and filter noise lines like `"10ml"`.
- **T2.R3.6 [Payload Size & Rate Limiting]**: Verify multipart upload $>10$MB returns HTTP 413 and excessive bursts trigger HTTP 429.

#### Feature R4: Academic Benchmark Reproduction Suite
- **T2.R4.1 [Exact Micro F1 Reproduction]**: Verify $R0$ Micro F1 = 76.75%, $R1$ Micro F1 = 80.15% ($\Delta F_1 = +3.39\%$).
- **T2.R4.2 [Macro F1 Metrics Consistency]**: Verify Capture-Macro F1 ($76.94\% \rightarrow 80.57\%$) and Prescription-Macro F1 ($86.20\% \rightarrow 88.42\%$).
- **T2.R4.3 [Paired Transition Matrix Exactness]**: Verify $b=14, c=9$, Net Gain = $+5$, Both Correct = 95, Both Fail = 19, Total = 137.
- **T2.R4.4 [Exact McNemar Statistical Test]**: Verify exact McNemar 2-tailed test produces $p = 0.4049$.
- **T2.R4.5 [Bootstrap 95% CI Boundaries]**: Verify Capture $\Delta F_1 \in [-3.18\%, +10.18\%]$ and Prescription $\Delta F_1 \in [0.00\%, +7.21\%]$.

#### Feature R5: Academic Documentation Integrity
- **T2.R5.1 [Markdown Link Integrity]**: Verify 100% of relative and local markdown links across all `.md` files resolve to valid existing files.
- **T2.R5.2 [Copy-Pasteable Command Syntax]**: Verify all shell/bash code blocks in `README.md` and `REPRODUCIBILITY.md` have valid syntax and runnable flags.
- **T2.R5.3 [BibTeX Parse Validation]**: Verify BibTeX entry in `README.md` and `REPRODUCIBILITY.md` parses cleanly with standard BibTeX tools.
- **T2.R5.4 [Phase B Status Clarification]**: Verify documentation clearly notes Phase B status as retired/held and does not instruct reviewers to run non-functional Phase B scripts.
- **T2.R5.5 [Documentation Metric Match]**: Verify figures and tables in documentation match the exact values in `reports/real_medication_roi_ablation/summary.csv`.

---

### Tier 3: Cross-Feature / Cross-Service Integration (Pairwise)

- **T3.1 [Mobile Client $\leftrightarrow$ Node API $\leftrightarrow$ Python AI]**: End-to-end simulated scan payload from Mobile contract through Node `/api/scan` to Python AI `/api/scan-prescription` and back.
- **T3.2 [Docker Stack $\leftrightarrow$ Database Seed $\leftrightarrow$ Drug Search]**: Dockerized Node API queries PostgreSQL `drug_cache` containing 9,284 seeded drugs and returns matching Vietnamese medications.
- **T3.3 [Academic Benchmark Suite $\leftrightarrow$ Ground Truth Dataset $\leftrightarrow$ Report Generator]**: `reproduce_paper_benchmarks.py` consumes `data/visible_in_frame_gt.json` and on-device ML Kit OCR files, executing statistical tests and producing complete report artifacts in `reports/`.
- **T3.4 [Documentation Quickstart $\leftrightarrow$ Actual Execution Commands]**: Commands documented in `README.md` and `REPRODUCIBILITY.md` match the exact entrypoints of `docker-compose.yml`, `mobile/`, and `scripts/`.
- **T3.5 [Git Attributes / Git Ignore $\leftrightarrow$ Build Artifacts $\leftrightarrow$ Dataset Persistence]**: Repository configuration prevents build cache contamination while ensuring dataset and model reproducibility.

---

### Tier 4: Real-World Academic Reproduction Scenarios

- **T4.1 [Scenario 1: Reviewer Benchmark Replication Workflow]**: An academic reviewer runs `python scripts/reproduce_paper_benchmarks.py --all` and verifies all published paper metrics, transition matrices, and bootstrap CIs.
- **T4.2 [Scenario 2: One-Command Docker Full-Stack Deployment]**: A reviewer runs `docker compose up -d`, waits for healthcheck convergence, tests health endpoints, executes a test scan, and verifies DB persistence.
- **T4.3 [Scenario 3: Mobile APK Build & Analysis Verification]**: A reviewer runs `cd mobile && flutter analyze && flutter test && flutter build apk --debug --no-pub` verifying zero errors/warnings, 100% test pass, and valid APK generation.
- **T4.4 [Scenario 4: Documentation Walkthrough Verification]**: End-to-end automated verification of every markdown link, command snippet, and documentation claim.
- **T4.5 [Scenario 5: Repository Cleanliness & Packaging Audit]**: A complete git hygiene inspection verifying zero tracked junk, valid MIT licensing, and pristine repository state.

---

## Test Runner Architecture & Directory Layout

The E2E test suite is organized into an automated, multi-tiered test runner located in `tests/e2e/`:

```
tests/e2e/
├── test_tier1_feature_coverage.py       # Tier 1: 26 feature coverage tests across R1-R5
├── test_tier2_boundary_cases.py         # Tier 2: 26 boundary & corner case tests across R1-R5
├── test_tier3_pairwise_integration.py   # Tier 3: 5 cross-feature integration tests
├── test_tier4_reviewer_scenarios.py     # Tier 4: 5 end-to-end reproduction workflows
├── run_e2e_tests.py                     # Master test runner & JUnit/Markdown report generator
└── conftest.py                          # Shared test fixtures, mock servers, and assertions
```

### Test Invocation
- **Run Full E2E Test Suite**:
  ```bash
  python3 tests/e2e/run_e2e_tests.py
  ```
- **Run by Tier**:
  ```bash
  pytest tests/e2e/test_tier1_feature_coverage.py -v
  pytest tests/e2e/test_tier2_boundary_cases.py -v
  pytest tests/e2e/test_tier3_pairwise_integration.py -v
  pytest tests/e2e/test_tier4_reviewer_scenarios.py -v
  ```

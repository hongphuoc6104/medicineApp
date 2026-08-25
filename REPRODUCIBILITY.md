# MedicineApp: Artifact Evaluation & Experimental Replication Guide

> **Paper Title:** *MedicineApp: On-Device Document Intelligence and Edge-Cloud Biomedical Named Entity Recognition for Clinical Prescription Digitization*  
> **Target Audience:** Independent Reviewers, Artifact Evaluators, and Reproducibility Chairs.  
> **License:** [MIT License](LICENSE)  
> **Repository:** [https://github.com/hongphuoc6104/medicineApp](https://github.com/hongphuoc6104/medicineApp)

---

## 📋 Table of Contents

1. [System & Hardware Requirements](#1-system--hardware-requirements)
2. [Reproduction Checklist](#2-reproduction-checklist)
3. [Step 1: One-Command Microservices Deployment (Docker Compose)](#3-step-1-one-command-microservices-deployment-docker-compose)
4. [Step 2: Dataset Verification & Human Provenance Audit](#4-step-2-dataset-verification--human-provenance-audit)
5. [Step 3: Benchmark Reproduction & Statistical Analysis](#5-step-3-benchmark-reproduction--statistical-analysis)
   - [Experiment A: Hard Camera ROI Intervention Study (R0 vs R1)](#experiment-a-hard-camera-roi-intervention-study-r0-vs-r1)
   - [Experiment B: Real ML Kit Layout Reconstruction Ablation (P0-P3)](#experiment-b-real-ml-kit-layout-reconstruction-ablation-p0-p3)
6. [Step 4: Mobile Application Build & Test Suite Verification](#6-step-4-mobile-application-build--test-suite-verification)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [Troubleshooting & Frequently Asked Questions (FAQs)](#8-troubleshooting--frequently-asked-questions-faqs)

---

## 1. System & Hardware Requirements

### Hardware Requirements

| Resource | Minimum Requirement | Recommended Specification | Purpose |
| :--- | :--- | :--- | :--- |
| **CPU** | 4-Core x86_64 or ARM64 | 8-Core Intel i7/Ryzen 7 / Apple Silicon | FastAPI AI Proxy (CPU mode) & Node.js |
| **RAM** | 8 GB System Memory | 16 GB System Memory | Full Docker stack + Android Emulator |
| **Disk Space** | 10 GB Free Storage | 20 GB Free Storage | Docker images, model weights, datasets |
| **GPU** | *Not Required (100% CPU)* | NVIDIA RTX with CUDA 12.x | Optional: GPU accelerated inference |

### Software Prerequisites

| Dependency | Required Version | Verification Command | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 22.04+), macOS 13+, Win 11 (WSL2) | `uname -a` | Linux / macOS native recommended |
| **Docker Engine** | `24.0.0+` | `docker --version` | Required for turnkey microservices |
| **Docker Compose** | `v2.20.0+` (Compose v2) | `docker compose version` | Integrated compose plugin |
| **Python** | `3.12.x` | `python3 --version` | For CLI benchmark execution |
| **Node.js** | `20.x LTS` (npm `10.x`) | `node -v && npm -v` | For local backend execution |
| **Flutter SDK** | `3.38.x` (Dart `3.10.x`) | `flutter --version` | For mobile client compilation |
| **Java JDK** | `OpenJDK 17` or `OpenJDK 21` | `java -version` | For Android Gradle builds |

---

## 2. Reproduction Checklist

- [ ] **Docker Stack Up**: PostgreSQL 16, Node.js API (3000), FastAPI AI Proxy (8000) are healthy.
- [ ] **Dataset Verification**: 9,284 DAV medications and 137 visible-in-frame ground truth items validated.
- [ ] **Provenance Trail**: `data/human_verification_provenance_log.json` verified with zero circular bias.
- [ ] **ROI Benchmark**: $R0$ vs $R1$ evaluation reproduces exact micro/macro $F_1$, McNemar $p = 0.4049$, and bootstrap CIs.
- [ ] **Layout Benchmark**: $P0-P3$ ablation reproduces baseline tables.
- [ ] **Mobile Quality Gate**: `flutter analyze` reports 0 issues, `flutter test` passes 39/39 tests.
- [ ] **Node Backend Gate**: `npm test` passes 55/55 unit and integration tests.

---

## 3. Step 1: One-Command Microservices Deployment (Docker Compose)

The entire backend infrastructure is containerized and orchestrated via `docker-compose.yml`.

### 3.1 Launch the Unified Stack

```bash
# Clone the repository
git clone https://github.com/hongphuoc6104/medicineApp.git
cd medicineApp

# Boot all services in the background (auto-builds, migrates DB, seeds 9,284 drugs)
docker compose up -d --build
```

### 3.2 Verify Container Health

Wait $\approx 15-20\text{ seconds}$ for internal health checks to transition to `healthy`:

```bash
docker compose ps
```

*Expected output:*
```
NAME               IMAGE                   COMMAND                  SERVICE      CREATED          STATUS                    PORTS
medicineapp_ai     medicineapp-python-ai   "python -m server.ma…"   python-ai    20 seconds ago   Up 20 seconds (healthy)   0.0.0.0:8000->8000/tcp
medicineapp_db     postgres:16-alpine      "docker-entrypoint.s…"   postgres     20 seconds ago   Up 20 seconds (healthy)   0.0.0.0:5432->5432/tcp
medicineapp_node   medicineapp-node-api    "docker-entrypoint.s…"   node-api     20 seconds ago   Up 20 seconds (healthy)   0.0.0.0:3000->3000/tcp
```

### 3.3 Liveness & Readiness Verification

Execute HTTP health probes against the running containers:

```bash
# 1. Node.js Express Gateway
curl -s -f http://localhost:3000/api/health | jq .

# 2. Python FastAPI AI Proxy
curl -s -f http://localhost:8000/api/health | jq .
```

*Expected JSON Responses:*
```json
{
  "success": true,
  "message": "Node.js API Gateway is healthy",
  "timestamp": "2026-08-24T13:30:00.000Z"
}
```
```json
{
  "status": "healthy",
  "model_loaded": true,
  "database_size": 9284
}
```

### 3.4 Automated Database Migration & Seeding Verification

The Node.js container automatically migrates table schemas and seeds the 9,284 drug registry on boot:

```bash
docker compose logs node-api | grep -E "(Migration|Seeding|Listening)"
```

*Expected log lines:*
```
[Database] Running pending migrations...
[Database] Migrations applied successfully.
[Database] 9,284 Vietnamese drug records loaded into drug_cache table.
[Server] Express API gateway listening on port 3000 in development mode.
```

### 3.5 Teardown Instructions

```bash
# Stop containers and remove network/volumes
docker compose down -v
```

---

## 4. Step 2: Dataset Verification & Human Provenance Audit

MedicineApp relies on an authoritative drug database and a strictly audited human ground truth dataset.

### 4.1 Canonical Data Files

| File Path | Entity Count | Description |
| :--- | :---: | :--- |
| `data/drug_db_vn_full.json` | 9,284 records | Complete Drug Administration of Vietnam (DAV) drug database with trade names (`tenThuoc`), active ingredients (`hoatChat`), concentrations (`nongDo`), and registration codes (`soDangKy`). |
| `data/visible_in_frame_gt.json` | 137 entities | Human-annotated ground truth of physically readable drug entities across 30 hard smartphone captures. |
| `data/human_verification_provenance_log.json` | 30 captures | Cryptographic/metadata provenance log confirming independent visual verification without circular model dependencies. |
| `reports/real_medication_roi_ablation/mlkit_ocr/` | 60 JSON files | On-device Google ML Kit text recognition JSON captures ($30\times R0$ full-page and $30\times R1$ table ROI crops). |

### 4.2 Execute Provenance Audit Script

Run the independent visual audit tool to verify the integrity and non-circularity of the ground truth:

```bash
source venv/bin/activate
PYTHONPATH=. python scripts/audit_visible_gt.py \
  --annotator "Artifact Reviewer" \
  --role "Independent Evaluator" \
  --out data/human_verification_provenance_log.json
```

*Expected output:*
```
[Audit] Loaded 30 hard camera captures from data/visible_in_frame_gt.json
[Audit] Evaluated 137 physically visible drug entities across 5 distinct clinical prescriptions.
[Audit] Provenance audit passed: 100% compliant with visual inclusion criteria.
[Audit] Audit log saved to data/human_verification_provenance_log.json
```

---

## 5. Step 3: Benchmark Reproduction & Statistical Analysis

### Experiment A: Hard Camera ROI Intervention Study (R0 vs R1)

This experiment evaluates the clinical utility of localized **Medication Table ROI cropping and 2nd-pass OCR ($R1$)** versus **Full-Page Smartphone capture ($R0$)** across 30 challenging real camera captures.

#### Execution Command:

```bash
source venv/bin/activate
PYTHONPATH=. python scripts/benchmark_real_medication_roi.py \
  --ocr-dir reports/real_medication_roi_ablation/mlkit_ocr \
  --visible-gt data/visible_in_frame_gt.json \
  --output-dir reports/real_medication_roi_ablation \
  --bootstrap 10000
```

#### Output Artifact Locations:

- `reports/real_medication_roi_ablation/summary.csv`
- `reports/real_medication_roi_ablation/failure_taxonomy.csv`
- `reports/real_medication_roi_ablation/paired_transition_matrix.csv`
- `reports/real_medication_roi_ablation/statistical_significance.json`
- `reports/real_medication_roi_ablation/r1_recovered_drugs.json`

#### Verifiable Paper Target Numbers:

1. **Multi-Granularity Summary (`summary.csv`)**:
   - **Drug-Instance Micro**:
     - $R0$: Precision = $77.61\%$, Recall = $75.91\%$, $F_1 = 76.75\%$
     - $R1$: Precision = $80.74\%$, Recall = $79.56\%$, $F_1 = 80.15\%$ ($\Delta F_1 = +3.40\%$)
   - **Capture-Macro**:
     - $R0$: Precision = $77.83\%$, Recall = $77.00\%$, $F_1 = 76.94\%$
     - $R1$: Precision = $81.00\%$, Recall = $81.00\%$, $F_1 = 80.57\%$ ($\Delta F_1 = +3.63\%$)
   - **Prescription-Macro**:
     - $R0$: Precision = $82.13\%$, Recall = $92.07\%$, $F_1 = 86.20\%$
     - $R1$: Precision = $84.28\%$, Recall = $94.34\%$ $F_1 = 88.42\%$ ($\Delta F_1 = +2.22\%$)

2. **Paired Drug Transition Matrix (`paired_transition_matrix.csv`)**:
   - Both $R0$ & $R1$ Succeeded: $95$ drugs
   - Both $R0$ & $R1$ Failed: $19$ drugs
   - $R1$ Recovered (Gain, $b$): $14$ drugs
   - $R1$ Missed (Loss, $c$): $9$ drugs

3. **Statistical Significance & CIs (`statistical_significance.json`)**:
   - Exact 2-sided McNemar / Binomial Test: $p = 0.4049$
   - 10,000-Iteration Capture-Level Bootstrap 95% CI on $\Delta F_1$: $[-0.92\%, +8.47\%]$ (Point: $+3.63\%$)
   - 10,000-Iteration Prescription-Clustered Bootstrap 95% CI on $\Delta F_1$: $[-3.22\%, +7.43\%]$ (Point: $+2.22\%$)

---

### Experiment B: Real ML Kit Layout Reconstruction Ablation (P0-P3)

This ablation benchmarks four distinct geometric reconstruction strategies for processing on-device OCR lines into structured clinical tokens:
- **$P0$**: Raw ML Kit text line concatenation.
- **$P1$**: Vertical coordinate-sorted line reconstruction.
- **$P2$**: Bounding box vertical threshold clustering.
- **$P3$**: Anchor-guided medication band grouping with sequence STT indexing.

#### Execution Command:

```bash
source venv/bin/activate
PYTHONPATH=. python scripts/benchmark_real_mlkit_layout.py \
  --output-dir reports/real_layout_ablation \
  --split val
```

#### Output Artifact Locations:

- `reports/real_layout_ablation/summary.csv`
- `reports/real_layout_ablation/failure_taxonomy.csv`
- `reports/real_layout_ablation/per_capture.csv`
- `reports/real_layout_ablation/per_prescription.csv`

#### Verifiable Paper Target Numbers:

| Strategy | Micro Prec | Micro Rec | Micro F1 | Macro Prec | Macro Rec | Macro F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$P0$** | $89.36\%$ | $30.02\%$ | **$44.94\%$** | $84.02\%$ | $82.36\%$ | **$78.29\%$** |
| **$P1$** | $89.36\%$ | $30.02\%$ | **$44.94\%$** | $84.02\%$ | $82.36\%$ | **$78.29\%$** |
| **$P2$** | $82.79\%$ | $25.49\%$ | **$38.98\%$** | $83.16\%$ | $56.29\%$ | **$63.81\%$** |
| **$P3$** | $90.63\%$ | $19.59\%$ | **$32.22\%$** | $85.16\%$ | $54.81\%$ | **$62.10\%$** |

---

## 6. Step 4: Mobile Application Build & Test Suite Verification

The mobile client is built with Flutter and communicates with the backend via REST multipart uploads.

### 6.1 Install Dependencies & Run Static Analysis

```bash
cd mobile
flutter pub get
flutter analyze
```

*Expected output:*
```
Analyzing mobile...
No issues found! (ran in 1.4s)
```

### 6.2 Execute Mobile Unit & Widget Test Suite

Run all 39 automated tests covering repositories, state notifiers, scan review UI, and notification schedules:

```bash
flutter test
```

*Expected output:*
```
00:04 +39: All tests passed!
```

### 6.3 Build Android APK Packages

Compile debug and release standalone APK binaries:

```bash
# Debug APK (for testing with USB debugging or emulator)
flutter build apk --debug

# Release APK (optimized with tree-shaking and minification)
flutter build apk --release
```

Generated APKs are located at:
- `mobile/build/app/outputs/flutter-apk/app-debug.apk`
- `mobile/build/app/outputs/flutter-apk/app-release.apk`

---

## 7. Environment Variables Reference

### Root & Docker Environment (`.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `postgres` | PostgreSQL superuser username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL superuser password |
| `POSTGRES_DB` | `medicine_app` | Relational database schema name |
| `POSTGRES_PORT` | `5432` | Host port mapped to PostgreSQL |
| `PYTHON_PORT` | `8000` | Host port mapped to FastAPI AI Proxy |
| `DEVICE` | `cpu` | PyTorch execution device (`cpu` or `cuda`) |
| `NODE_PORT` | `3000` | Host port mapped to Node.js API Gateway |
| `NODE_ENV` | `development` | Environment mode (`development` / `production`) |
| `JWT_SECRET` | *(string)* | Secret key for signing and verifying JWT tokens |

### Mobile Client Environment (`mobile/.env`)

| Variable | Recommended Target | Value |
| :--- | :--- | :--- |
| `API_BASE_URL` | Android Emulator (AVD) with Docker | `http://10.0.2.2:3000/api` |
| `API_BASE_URL` | Android Emulator (AVD) with `dev.sh` | `http://10.0.2.2:3001/api` |
| `API_BASE_URL` | Physical Device via USB Reverse ADB | `http://127.0.0.1:3000/api` |
| `API_BASE_URL` | Physical Device via Wi-Fi LAN | `http://<YOUR_PC_LAN_IP>:3000/api` |

---

## 8. Troubleshooting & Frequently Asked Questions (FAQs)

### Q1: Port 5432, 3000, or 8000 is already in use.
**Solution:** Check and kill existing processes bound to these ports or alter the port mappings in `.env`:
```bash
# Check port binding on Linux/macOS
lsof -i :3000
lsof -i :8000
lsof -i :5432

# Or stop conflicting local PostgreSQL instances
sudo systemctl stop postgresql
```

### Q2: How do I test the mobile app on a physical Android phone?
**Solution:** Connect phone via USB with USB Debugging enabled, then configure ADB reverse port forwarding:
```bash
adb reverse tcp:3000 tcp:3000
```
In `mobile/.env`, set `API_BASE_URL=http://127.0.0.1:3000/api`. The mobile app can now reach the Docker backend on localhost.

### Q3: ML Kit Document Scanner does not launch on an Android Emulator.
**Solution:** The ML Kit Document Scanner requires Google Play Services. In Android Studio AVD Manager, create an emulator with the **"Google Play"** or **"Google APIs"** system image (API 34/35). Standard AOSP images lack Play Services binaries.

### Q4: Can I run PhoBERT inference on GPU instead of CPU?
**Solution:** Yes. If you have an NVIDIA GPU with the NVIDIA Container Toolkit installed:
```bash
docker compose -f docker-compose.gpu.yml up -d --build
```
Alternatively, in local Python environments, ensure PyTorch with CUDA is installed; the pipeline auto-detects CUDA when `DEVICE="cuda"`.

### Q5: How do I re-run database migrations and reload drug seeds cleanly?
**Solution:**
```bash
# Teardown database volume
docker compose down -v
# Relaunch with clean initialization
docker compose up -d --build
```

# AGENTS.md — AI Agent Onboarding Guide

> **ĐỌC FILE NÀY TRƯỚC KHI LÀM BẤT CỨ GÌ.** File này dành cho AI agents. Chứa toàn bộ bối cảnh, lịch sử, quyết định kỹ thuật, lỗi đã gặp, và các quy tắc bắt buộc.

---

## 1. Tổng quan

**MedicineApp** — Ứng dụng quét đơn thuốc (Phase A) và xác minh viên thuốc (Phase B).
**Hiện tại chỉ tập trung Phase A.** Phase B đang hold.

---

## 2. Cây Thư mục (2 cấp)

```
medicineApp/
├── core/                    # ★ SOURCE CODE CHÍNH (Python AI Pipeline)
│   ├── phase_a/             #   Pipeline quét đơn thuốc (4 bước)
│   │   ├── s1_detect/       #     Bước 1: YOLO crop
│   │   ├── s2_preprocess/   #     Bước 2: Deskew + orientation
│   │   ├── s3_ocr/          #     Bước 3: PaddleOCR + VietOCR
│   │   ├── s5_classify/     #     Bước 4: PhoBERT NER
│   │   └── s6_drug_search/  #     Bước 5 (optional): fuzzy-match tên chuẩn
│   ├── phase_b/             #   [HOLD] Xác minh viên thuốc
│   ├── shared/              #   zero_pima_loader (Phase B only)
│   ├── config.py            #   Cấu hình: CONF_THRESHOLD=0.50, paths
│   └── pipeline.py          #   API orchestrator cho FastAPI
│
├── scripts/                 # ★ SCRIPTS CHẠY
│   ├── run_pipeline.py      #   CLI chính — chạy Phase A
│   ├── benchmark_pipeline.py #   Benchmark: chạy tất cả ảnh → JSON report
│   ├── crawl_drug_vn.py     #   ★ Crawl 9,284 thuốc VN từ ddi.lab.io.vn
│   ├── train_ner.py         #   Train PhoBERT NER model
│   ├── prepare_ner_data.py  #   Chuẩn bị data NER từ VAIPE
│   ├── build_drug_db.py     #   Build drug database CSV
│   └── build_full_drug_db.py
│
├── server/                  # ★ FASTAPI SERVER (Python — AI proxy)
│   ├── main.py              #   Entry point, routes
│   ├── routers/             #   API endpoints
│   ├── schemas/             #   Pydantic models
│   └── services/            #   Business logic
│
├── server-node/             # ★ NODE.JS API SERVER (Express — Main backend)
│   ├── src/
│   │   ├── config/          #   env.js, database.js, migrate.js, seed.js
│   │   ├── middleware/      #   auth.js, rateLimiter.js, errorHandler.js, logger.js, validator.js
│   │   ├── routes/          #   health, auth, drug, scan, plan routes
│   │   ├── services/        #   auth, drug, scan, plan services
│   │   ├── utils/           #   errors.js, response.js
│   │   ├── app.js           #   Express app (no listen)
│   │   └── server.js        #   HTTP listener entry point
│   ├── tests/               #   55 tests (3 unit + 3 integration)
│   ├── docker-compose.yml   #   PostgreSQL 16
│   ├── package.json
│   └── .env.example
│
├── models/                  # ★ MODEL WEIGHTS (KHÔNG COMMIT GIT)
│   ├── yolo/best.pt         #   6MB  — YOLO detect
│   ├── phobert_ner_model/   #   500MB — PhoBERT NER
│   └── zero_pima/           #   521MB — Phase B only
│
├── data/                    # ★ DATA
│   ├── input/               #   50 ảnh test (7 folders prescription_1..7)
│   ├── output/phase_a/      #   Output pipeline (JSON + ảnh)
│   ├── ner_dataset/         #   Dataset đã xử lý cho train NER
│   ├── drug_db_vn.csv       #   DB thuốc (316 thuốc, cũ)
│   ├── drug_db_vn_full.json #   ★ DB thuốc đầy đủ (9,284 thuốc, crawl từ ddi.lab.io.vn)
│   ├── vaipe_drugs_kb.json  #   Knowledge base thuốc VAIPE
│   └── createPrescription/  #   Script tạo đơn thuốc giả
│
├── docker-compose.yml       # PostgreSQL 16 Alpine (development)
├── docs/                    # Tài liệu chi tiết
├── archive/                 # Code cũ đã bỏ (KHÔNG DÙNG)
├── Zero-PIMA/               # [KHÔNG SỬA] Dependency Phase B
├── VAIPE_Full/              # [KHÔNG SỬA] Dataset VAIPE gốc (21.9GB)
├── tests/                   # Unit tests Python (16 tests)
├── AGENTS.md                # ← BẠN ĐANG ĐỌC FILE NÀY
├── PIPELINE_STATUS.md       # Tài liệu kỹ thuật pipeline
└── README.md                # README gốc (83KB, CÓ THỂ LỖI THỜI)
```

---

## 3. Pipeline Phase A — 4 Bước

```
📷 Ảnh đơn thuốc
  → [1] YOLO Detect & Crop     (core/phase_a/s1_detect/)
  → [2] Preprocess              (core/phase_a/s2_preprocess/)
  → [3] Hybrid OCR              (core/phase_a/s3_ocr/ocr_engine.py)
       PaddleOCR detect polygons → crop → VietOCR recognize tiếng Việt
  → [4] PhoBERT NER Classify    (core/phase_a/s5_classify/ner_extractor.py)
       drugname / other
  → [+] Drug Search (optional)  (core/phase_a/s6_drug_search/)
       fuzzy-match tên thuốc → drug_db_vn.csv → tên chuẩn
  → 📋 JSON danh sách thuốc (data/output/phase_a/<tên_ảnh>/)
```

> ⚠️ **Folder đánh số nhảy từ s3 → s5**: `s4_grouping/` đã bị xóa và dời vào archive. Tên folder `s5_classify/` giữ nguyên để không thay đổi git history.

---

## 4. Lịch sử Quyết định & Phần Đã Xóa

| Thay đổi | Lý do | Hành động AI |
|----------|-------|--------------|
| **BỎ GCN** (Graph Neural Net) | Kết quả tệ trên dataset tiếng Việt nhỏ, rườm rà | **KHÔNG** đề xuất dùng lại GCN. File đã dời → `archive/deprecated_gcn/` |
| **BỎ s4_grouping** (merge text blocks) | PhoBERT NER xử lý từng block độc lập tốt hơn | **KHÔNG** tạo lại grouping module |
| **GCN → PhoBERT NER** | NER đạt F1=100% trên test set, nhanh hơn, đơn giản hơn | `s5_classify/` giờ chỉ chứa `ner_extractor.py` |
| **CRAFT → PaddleOCR** | PaddleOCR PP-OCRv5 detect line-level polygons chính xác hơn CRAFT | OCR engine giờ dùng `HybridOcrModule` |

### Thư mục Archive (chi tiết)

```
archive/
├── deprecated_gcn/          # GCN classifier + evaluate script đã bỏ
├── legacy/                  # Code pipeline cũ
├── scripts/                 # Scripts cũ không dùng
├── notebooks/               # Notebook cũ
├── weights/                 # Weights cũ
└── YOLO11-Seg-Label-Detector-main/  # Tool label YOLO (đã dùng xong)
```

---

## 5. Data Map

| File/Folder | Dùng cho | Ghi chú |
|-------------|----------|---------|
| `data/input/` | 51 ảnh test đơn thuốc thật | 7 folders `prescription_1..7` |
| `data/output/phase_a/<img>/` | Output pipeline mỗi ảnh | Có thể xóa để chạy lại |
| `data/output/phase_a/<img>/summary.json` | **Kết quả cuối** — list thuốc, timing | Schema chính để đọc |
| `data/output/phase_a/<img>/step-3_ocr.json` | OCR text blocks thô | `[{text, bbox, confidence}]` |
| `data/output/phase_a/<img>/step-4_ner_classify.json` | NER label từng block | `[{text, label, confidence, bbox}]` |
| `data/ner_dataset/` | Dataset train PhoBERT NER | Đã xử lý sẵn |
| `data/drug_db_vn_full.json` | **★ Database thuốc VN đầy đủ** (9,284 thuốc) | Crawl từ ddi.lab.io.vn, 2026-03-10 |
| `data/drug_db_vn.csv` | Database thuốc cũ (316 thuốc) | Phụ | 
| `data/vaipe_drugs_kb.json` | Knowledge base thuốc VAIPE | Reference |
| `data/pres/` | Test dataset đơn thuốc (118 đơn BVĐK) | Dùng để evaluate model |
| `data/pills/` | Ảnh viên thuốc | Cho Phase B (chưa dùng) |
| `data/createPrescription/` | Script tạo đơn thuốc giả (synthetic) | Dùng 1 lần |
| `VAIPE_Full/` | Dataset VAIPE gốc (21.9GB ảnh+label) | **KHÔNG SỬA, KHÔNG XÓA** |

---

## 6. NER Training Info

| Item | Giá trị |
|------|---------|
| Base model | `vinai/phobert-base-v2` |
| Script train | `scripts/train_ner.py` |
| Script chuẩn bị data | `scripts/prepare_ner_data.py` |
| Dataset | `data/ner_dataset/` (từ VAIPE) |
| Labels | `B-DRUG`, `I-DRUG`, `O` (BIO format) |
| Kết quả | F1 = 100% trên test set |
| Weights output | `models/phobert_ner_model/` |

---

## 7. Known Issues & Pending Tasks

| # | Vấn đề | Trạng thái | Chi tiết |
|---|--------|------------|----------|
| 1 | ~~Chữ cong bị cắt lẹm~~ | ✅ Đã fix | `_crop_polygon()` đã đổi sang Perspective Transform |
| 2 | ~~Bug 0 drugs (IMG_180633)~~ | ✅ Đã fix | Hạ CONF_THRESHOLD + YOLO fallback → giờ detect 1 drug |
| 3 | **PaddleOCR load rec model thừa** | ⚠️ Giới hạn API | Không tắt được, tốn thêm 2-3s cold start |
| 4 | **Phase B không hoạt động** | 🔒 Hold | Thiếu contrastive matching. KHÔNG SỬA trừ khi user yêu cầu |
| 5 | ~~YOLO fail → error~~ | ✅ Đã fix | Pipeline giờ fallback dùng full image |
| 6 | ~~Pipeline bỏ qua preprocess~~ | ✅ Đã fix | Đã thêm deskew + orientation vào pipeline |
| 7 | ~~NER trả key "box" vs "bbox"~~ | ✅ Đã fix | Thống nhất dùng "bbox" |
| 8 | ~~Server cold start 13s~~ | ✅ Đã fix | Warm-up models trong lifespan() + Semaphore(1) chống OOM |

> **Benchmark sau fix (2026-03-10):** 50/50 ảnh thành công, 338 drugs, avg 6.8/ảnh, 0 errors.

---

## 8. Documentation Map

| File | Đọc khi nào |
|------|------------|
| `AGENTS.md` (file này) | **Luôn đọc đầu tiên** |
| `PIPELINE_STATUS.md` | Khi cần biết chi tiết kỹ thuật từng bước, args, versions |
| `docs/project_status.md` | Khi cần checklist tiến độ (Đã làm / Chưa làm) |
| `docs/master_plan.md` | Khi cần hiểu bức tranh tổng thể thiết kế ban đầu |
| `models/README.md` | Khi cần biết weights nào, dung lượng, load ở đâu |
| `README.md` (root) | ⚠️ 83KB, có thể lỗi thời ở 1 số phần — ưu tiên AGENTS.md |

---

## 9. Lệnh Chạy

```bash
source venv/bin/activate

# Phase A — 1 ảnh
python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg

# Phase A — 1 folder
python scripts/run_pipeline.py --dir data/input/prescription_3

# Phase A — tất cả 51 ảnh
python scripts/run_pipeline.py --all

# FastAPI server (Python AI proxy)
python -m server.main

# Node.js server (Main backend)
cd server-node && npm run dev

# Node.js tests (55 tests)
cd server-node && npm test

# PostgreSQL Docker
docker compose up -d postgres

# Seed drug data
cd server-node && npm run seed
```

## 10. Tech Stack

| Component | Chi tiết |
|-----------|---------|
| Python | 3.12 |
| Node.js | 20 (Express 4, ES modules) |
| PostgreSQL | 16 Alpine (Docker) |
| OCR Detect | PaddleOCR PP-OCRv5 mobile (`device=gpu`) |
| OCR Recognize | VietOCR vgg_transformer (`device=cuda`) |
| NER | PhoBERT-base-v2 fine-tuned (BIO tagging) |
| Object Detection | YOLOv11n-seg |
| Python Server | FastAPI + Semaphore(1) GPU concurrency limit |
| Node Server | Express + JWT + Zod + Helmet + Rate Limit |
| Database | PostgreSQL 16 (6 tables, pg_trgm fuzzy search) |
| GPU | RTX 3050 4GB (hoặc CPU fallback) |
| Cold start | ~17s/ảnh đầu (warm-up + model loading) |
| Warm | ~7s/ảnh (inference only) |
| Benchmark | 50/50 ảnh, 338 drugs, avg 6.8/ảnh, 0 errors |
| Node Tests  | 55/55 pass (26 unit + 29 integration) |

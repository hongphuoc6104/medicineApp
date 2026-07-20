# AGENTS.md — AI Agent Onboarding Guide

> **ĐỌC FILE NÀY TRƯỚC KHI LÀM BẤT CỨ GÌ.** File này dành cho AI agents. Chứa toàn bộ bối cảnh, lịch sử, quyết định kỹ thuật, lỗi đã gặp, và các quy tắc bắt buộc.

---

## 🔒 QUY TẮC VÀNG — BẮT BUỘC ĐỌC TRƯỚC KHI VIẾT CODE

> **AGENT PHẢI THỰC THI ĐÚNG CÁC NGUYÊN TẮC SAU MỖI KHI FIX BUG HOẶC PHÁT TRIỂN TÍNH NĂNG MỚI.**

### Nguyên tắc 1: Pipeline chính là BẤT KHẢ XÂM PHẠM

- File `scripts/run_pipeline.py` là **pipeline chính đã được kiểm thử bởi user**.
- **KHÔNG ĐƯỢC** xóa, refactor, hay thay thế logic hiện có. Chỉ được **THÊM** code.
- Trước khi sửa bất kỳ dòng nào, phải đọc toàn bộ hàm liên quan bằng `view_file`.
- Nếu cần khôi phục file → dùng `git show <commit>:path > /tmp/file.py` và so sánh thủ công. **KHÔNG** dùng `git checkout` mà không hỏi user trước.

### Nguyên tắc 2: Tính năng mới → Option Flag + Test File riêng

- Mọi tính năng thử nghiệm phải được bọc trong `--option` flag (ví dụ `--stop-after-ocr`, `--no-drug-lookup`).
- **Phải tạo file test riêng** tại `scripts/tests/test_<tính_năng>.py` trước khi tích hợp vào pipeline chính.
- File test có thể fail mà **không ảnh hưởng gì đến pipeline chính**.
- Khi test OK → mới tích hợp vào `run_pipeline.py`.

### Nguyên tắc 3: Trình tự bắt buộc khi có bug hoặc tính năng mới

```
1. Đọc AGENTS.md (file này) — nắm bối cảnh
2. Đọc code gốc liên quan bằng view_file — KHÔNG đoán, KHÔNG viết từ trí nhớ
3. Tạo scripts/tests/test_<feature>.py → chạy thử độc lập
4. Nếu test OK → mới THÊM (không thay thế!) vào pipeline chính
5. Chạy pipeline chính để xác nhận không bị regression
```

---

## 1. Tổng quan

**MedicineApp** — Ứng dụng quét đơn thuốc (Phase A) và xác minh viên thuốc (Phase B).
**Hiện tại chỉ tập trung Phase A.** Phase B đang hold.

---

## 2. Cây Thư mục (2 cấp)

```
medicineApp/
├── core/                    # ★ SOURCE CODE CHÍNH (Python AI Pipeline)
│   ├── classify/            #   Phân loại PhoBERT NER + STT grouping
│   ├── drug_search/         #   Fuzzy-match local drug database (9,284 thuốc)
│   ├── config.py            #   Cấu hình: paths
│   └── pipeline.py          #   API orchestrator cho FastAPI
│
├── scripts/                 # ★ SCRIPTS CHẠY
│   ├── run_pipeline.py      #   CLI chính — chạy Phase A
│   ├── benchmark_pipeline.py #   Benchmark: chạy tất cả ảnh → JSON report
│   ├── test_preprocess_robustness.py # Test độ bền bỉ Deskew + Orientation (Modulo 90)
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
│   ├── yolo/best.pt         #   YOLO detect đơn thuốc lớn (main)
│   ├── yolo/table_best.pt   #   YOLO detect bảng thuốc (ROI trước OCR)
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
├── archive/                 # Code cũ và dữ liệu không còn phù hợp
│   └── VAIPE_Full/          # Dời từ root vào đây (2026-03-16) do format không khớp thực tế
├── Zero-PIMA/               # [KHÔNG SỬA] Dependency Phase B
├── tests/                   # Unit tests Python (16 tests)
├── AGENTS.md                # ← BẠN ĐANG ĐỌC FILE NÀY
├── PIPELINE_STATUS.md       # Tài liệu kỹ thuật pipeline
└── README.md                # README gốc (83KB, CÓ THỂ LỖI THỜI)
```

---

## 3. Pipeline Tinh giản (Fast-Path OCR Text)

```
💬 Văn bản OCR từ máy di động (Client-side Google ML Kit Document Scanner & Text Recognition)
  → [1] Group OCR blocks by STT  (core/classify/stt_grouping.py)
       Tìm tọa độ Y của các số thứ tự STT (1, 2, 3...), sau đó gom TẤT CẢ các text block nằm lọt giữa STT 1 và STT 2 thành CÙNG 1 CHUỖI ngang.
  → [2] PhoBERT NER Classify    (core/classify/ner_extractor.py)
       Label hiện tại: drugname / other
  → [3] Drug Search             (core/drug_search/drug_lookup.py)
       fuzzy-match tên thuốc → drug_db_vn_full.json (9,284 thuốc VN)
       tenThuoc (tên thương mại) + hoatChat (generic) đều được search
  → [+] Resolution state
       confirmed / unmapped_candidate / rejected_noise
  → 📋 JSON danh sách thuốc
```

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
| `data/output/phase_a/<img>/step-3_ocr.json` | OCR text blocks thô | `[{text, bbox, confidence}]` — gồm `raw_block_count` và `block_count` (sau merge) |
| `data/output/phase_a/<img>/step-4_ner_classify.json` | NER label từng block | `[{text, label, confidence, bbox}]` |
| `data/output/phase_a/<img>/step-5_drug_search.json` | **★ Drug search results** — tên chuẩn DB | `[{ocr_text, matched_name, generic, score, so_dang_ky, source}]` |
| `data/ner_dataset/` | Dataset train PhoBERT NER (cũ) | Lấy từ VAIPE, cấu trúc ô rời rạc |
| `data/synthetic_train/` | **★ Dataset Train NER Mới** | 938 ảnh + JSON giả lập đúng format bảng thuốc thực tế (STT, Tên, SL, Cách dùng) |
| `data/drug_db_vn_full.json` | **★ Database thuốc VN đầy đủ** (9,284 thuốc) | Crawl từ ddi.lab.io.vn, 2026-03-10. Fields: `tenThuoc`, `hoatChat[{tenHoatChat, nongDo}]`, `soDangKy` |
| `data/drug_db_vn.csv` | Database thuốc cũ (316 thuốc) | Fallback nếu JSON không có | 
| `data/vaipe_drugs_kb.json` | Knowledge base thuốc VAIPE | Reference |
| `data/pres/` | Test dataset đơn thuốc (118 đơn BVĐK) | Dùng để evaluate model |
| `data/pills/` | Ảnh viên thuốc | Cho Phase B (chưa dùng) |
| `data/createPrescription/` | Script tạo đơn thuốc giả (synthetic) | Dùng 1 lần |
| `archive/VAIPE_Full/` | Dataset VAIPE gốc (21.9GB) | **Dời vào archive (2026-03-16)** vì không còn phù hợp format bảng thực tế |

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
| 9 | ~~Session scan mất trạng thái khi restart~~ | ✅ Đã fix | Session lưu DB (`scan_sessions`) thay vì in-memory nguồn chính |
| 10 | ROI-table chưa đủ ổn định để bật mặc định | ⚠️ Đang benchmark | Smoke test 2026-03-14: tốc độ có cải thiện nhẹ nhưng recall chưa ổn định |
| 11 | ~~`force_portrait()` xoay sai ảnh YOLO-crop~~ | ✅ Đã fix (2026-03-14) | **ROOT CAUSE BUG**: YOLO crop ảnh bảng thuốc landscape → `force_portrait()` xoay 90° → chữ nằm ngang → OCR chỉ ra ký tự đơn → 0 drugs. Fix: **bỏ `force_portrait()`**, dùng AI orientation `fix_orientation_ai()` (PP-LCNet 0°/90°/180°/270°) làm mặc định. |
| 12 | ~~OCR blocks rời rạc → NER không nhận tên thuốc nhiều từ~~ | 🔄 Đổi chiến lược | (Cũ: Gộp theo Y-axis). Hiện nay bỏ Y-axis vì sinh rác đối với chữ lơ lửng. Chiến lược mới: **Group by STT** (Gom mọi text nằm giữa 2 số STT thành 1 chuỗi liên tục) để match với dữ liệu train Synthetic. |
| 13 | ~~Drug Search chỉ có 316 thuốc~~ | ✅ Đã fix (2026-03-14) | `DrugLookup` nâng cấp từ CSV (316) → `drug_db_vn_full.json` (9,284 thuốc). Search cả tenThuoc + hoatChat. |
| 14 | ~~Deskew sai góc >15° và PP-LCNet chạy CPU quá chậm~~ | ✅ Đã fix (2026-03-14) | **Deskew**: Nâng cấp toán học Modulo 90 `(angle+45)%90-45` tự snap ảnh về phương dọc/ngang với mọi biên độ góc. **AI GPU**: Dùng `paddle.set_device('gpu')` tăng tốc PP-LCNet xuống `0.6s/ảnh` (Đạt 36/36 test cases). |
| 15 | ~~OCR Visualization lỗi Unicode (tiếng Việt)~~ | ✅ Đã fix (2026-03-15) | Dùng **PIL (Pillow)** thay cho `cv2.putText` để hiển thị đúng dấu tiếng Việt trên ảnh debug. |
| 16 | ~~Ảnh crop bị xóa đen lẹm vào nội dung~~ | ✅ Đã fix (2026-03-16) | Thay pixel-mask bằng **Convex Hull** (đa giác lồi nhỏ nhất). Đảm bảo giữ nguyên 100% pixel bên trong bảng, chỉ đen hóa vùng thực sự nằm ngoài đơn thuốc. |
| 17 | **NER nhầm lẫn Qty/Usage thành Drug** | ⚠️ Đang kiến trúc lại | Vấn đề 1: Nhầm vì NER cũ chỉ có label DRUG. Vấn đề 2: Format thực tế 2-3 dòng gây lệch ngữ nghĩa. Giải pháp TỔNG THỂ: **[Post-OCR]** Ép text thành 1 dòng liên tục bằng `Group by STT` + **[NER Model]** Re-train PhoBERT đa nhãn bằng `synthetic_train` (đã là text 1 dòng). |

> **Benchmark sau fix (2026-03-14):** prescription_3/IMG_20260209_180505.jpg → **5/5 drugs** (Celecoxib, Eperisone, Mecobalamin, Loratadine, Paracetamol), 5/5 tìm thấy trong DB 9,284 thuốc.
> **Benchmark trước đó (2026-03-10):** 50/50 ảnh thành công, 338 drugs, avg 6.8/ảnh, 0 errors.

---

## 8. Documentation Map

| File | Đọc khi nào |
|------|------------|
| `AGENTS.md` (file này) | **Luôn đọc đầu tiên** |
| `PIPELINE_STATUS.md` | Khi cần biết chi tiết kỹ thuật từng bước, args, versions |
| `docs/mlkit_progressive_ocr/README.md` | Mục lục duy nhất cho đợt nâng cấp ML Kit và Progressive OCR |
| `docs/mlkit_progressive_ocr/01_CONG_VIEC_CAN_LAM.md` | Checklist và trạng thái từng work package |
| `docs/mlkit_progressive_ocr/04_KE_HOACH_KIEM_THU.md` | Khi tạo hoặc chạy test cho pipeline mới |
| `docs/mlkit_progressive_ocr/05_DEBUG_VA_QUAN_SAT.md` | Khi debug từng stage hoặc đối chiếu artifact |
| `docs/mlkit_progressive_ocr/06_BENCHMARK_VA_DOI_CHIEU.md` | Khi benchmark A/B/C và quyết định giữ/xóa stage cũ |
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

# Test Benchmark chức năng Deskew Modulo 90 & Orientation AI
python scripts/test_preprocess_robustness.py

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
| Object Detection | YOLOv11n-seg (2 weights: main + table ROI) |
| Python Server | FastAPI + Semaphore(1) GPU concurrency limit |
| Node Server | Express + JWT + Zod + Helmet + Rate Limit |
| Database | PostgreSQL 16 (6 tables, pg_trgm fuzzy search) |
| GPU | RTX 3050 4GB (hoặc CPU fallback) |
| Cold start | ~17s/ảnh đầu (warm-up + model loading) |
| Warm | ~7s/ảnh (inference only) |
| Benchmark | 50/50 ảnh, 338 drugs, avg 6.8/ảnh, 0 errors |
| Node Tests  | 55/55 pass (26 unit + 29 integration) |

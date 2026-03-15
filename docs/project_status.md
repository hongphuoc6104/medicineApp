# MedicineApp — Project Status (Updated 2026-03-14)

## ✅ Đã hoàn thành

| Việc | File/Path chính | Ngày |
|------|----------------|------|
| YOLO11-seg detection model | `models/yolo/best.pt` | — |
| Hybrid OCR (PaddleOCR + VietOCR) | `core/phase_a/s3_ocr/` | — |
| **PhoBERT NER Classify** (thay GCN) | `core/phase_a/s5_classify/ner_extractor.py` | — |
| Drug Search (fuzzy match DB) | `core/phase_a/s6_drug_search/` | — |
| **Full inference pipeline (Phase A)** | `scripts/run_pipeline.py` | — |
| FastAPI server | `server/main.py` | — |
| VAIPE dataset (21.9GB) | Kaggle `kusnguyen/full-vaipe` | — |
| Zero-PIMA train 50 epoch (VAIPE) | `models/zero_pima/zero_pima_best.pth` | — |
| PhoBERT NER train (F1=100%) | `models/phobert_ner_model/` | — |
| Pipeline test 50 ảnh | 5-13 thuốc/ảnh, ~6.8s/ảnh | 2026-03-10 |
| OCR Polygon Unwarp (Perspective Transform) | `core/phase_a/s3_ocr/ocr_engine.py` | — |
| **Fix bug `force_portrait()` xoay sai ảnh YOLO-crop** | `core/phase_a/s2_preprocess/orientation.py` | 2026-03-14 |
| **`merge_into_lines()` — gộp OCR blocks thành dòng** | `core/phase_a/s3_ocr/ocr_engine.py` | 2026-03-14 |
| **DrugLookup nâng cấp → 9,284 thuốc VN** | `core/phase_a/s6_drug_search/drug_lookup.py` | 2026-03-14 |
| **Drug Search Step 5 tích hợp vào run_pipeline.py** | `scripts/run_pipeline.py` | 2026-03-14 |

## ⚠️ Quy tắc quan trọng — KHÔNG sai lần nữa

| Quy tắc | Giải thích |
|---------|-----------|
| **KHÔNG dùng `force_portrait()`** | Xoay sai ảnh YOLO-crop landscape → OCR chỉ ra ký tự đơn → 0 drugs |
| **Dùng `fix_orientation_ai()`** | PP-LCNet phân loại 4 góc (0°/90°/180°/270°) → xoay đúng |
| **Gọi `merge_into_lines()` sau OCR** | Gộp blocks cùng dòng Y-axis → NER nhận đúng tên thuốc nhiều từ |
| **DrugLookup dùng JSON** | `drug_db_vn_full.json` (9,284 thuốc), không phải CSV (316 thuốc cũ) |
| **Step 5 là Drug Search** | Có `step-5_drug_search.json` trong output, không phải optional nữa |

## 📦 Archived (không còn sử dụng trong Phase A)

| Module | Lý do | Vị trí |
|--------|-------|--------|
| `s4_grouping/` | NER classify trực tiếp OCR output | `archive/deprecated_gcn/` |
| `gcn_classifier.py` | Thay bằng PhoBERT NER | `archive/deprecated_gcn/` |
| `evaluate.py` | Script đánh giá GCN | `archive/deprecated_gcn/` |
| `force_portrait()` trong orientation.py | Gây bug xoay sai YOLO crop — **vẫn còn trong code nhưng KHÔNG được gọi** | `core/phase_a/s2_preprocess/orientation.py` |

## ⚠️ Phase B — Chưa hoạt động

- Code có sẵn: `core/phase_b/` (FRCNN detect + GCN match)
- Thiếu contrastive matching (patched `roi_heads.py`)
- Giữ nguyên, chờ nâng cấp riêng

## ❌ Chưa làm (theo ưu tiên)

| # | Việc | Ưu tiên |
|---|------|---------| 
| 1 | End-to-end test (In → Chụp → Pipeline) | 🟡 TB |
| 2 | Phase B activation (đang hold) | 🟡 TB |
| 3 | Flutter App integration với backend | 🟢 Thấp |
| 4 | Tinh chỉnh Drug Search: ưu tiên tên thương mại hơn generic | 🟡 TB |

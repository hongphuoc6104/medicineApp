# MedicineApp — Project Status (Updated 2026-03-08)

## ✅ Đã hoàn thành

| Việc | File/Path chính |
|------|----------------|
| YOLO11-seg detection model | `models/yolo/best.pt` |
| Hybrid OCR (PaddleOCR + VietOCR) | `core/phase_a/s3_ocr/` |
| **PhoBERT NER Classify** (thay GCN) | `core/phase_a/s5_classify/ner_extractor.py` |
| Drug Search (fuzzy match DB) | `core/phase_a/s6_drug_search/` |
| **Full inference pipeline (Phase A)** | `scripts/run_pipeline.py` |
| FastAPI server | `server/main.py` |
| VAIPE dataset (21.9GB) | Kaggle `kusnguyen/full-vaipe` |
| Zero-PIMA train 50 epoch (VAIPE) | `models/zero_pima/zero_pima_best.pth` |
| PhoBERT NER train (F1=100%) | `models/phobert_ner_model/` |
| Pipeline test 50 ảnh | 5-13 thuốc/ảnh, ~6.8s/ảnh |

## 📦 Archived (không còn sử dụng trong Phase A)

| Module | Lý do | Vị trí |
|--------|-------|--------|
| `s4_grouping/` | NER classify trực tiếp OCR output | `archive/deprecated_gcn/` |
| `gcn_classifier.py` | Thay bằng PhoBERT NER | `archive/deprecated_gcn/` |
| `evaluate.py` | Script đánh giá GCN | `archive/deprecated_gcn/` |

## ⚠️ Phase B — Chưa hoạt động

- Code có sẵn: `core/phase_b/` (FRCNN detect + GCN match)
- Thiếu contrastive matching (patched `roi_heads.py`)
- Giữ nguyên, chờ nâng cấp riêng

## ❌ Chưa làm (theo ưu tiên)

| # | Việc | Ưu tiên |
|---|------|---------| 
| 1 | OCR Polygon Unwarp (xử lý chữ cong) | 🔴 Cao |
| 2 | End-to-end test (In → Chụp → Pipeline) | 🟡 TB |
| 3 | Phase B activation | 🟡 TB |
| 4 | Flutter App | 🟢 Thấp |

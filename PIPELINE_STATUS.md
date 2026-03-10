# MedicineApp Pipeline — Tài Liệu Kỹ Thuật

> Last updated: 2026-03-10

## Kiến Trúc Tổng Quan

```
 PHASE A: QUÉT ĐƠN THUỐC (4 bước)
 ───────────────────────────────────
   📷 Ảnh đơn thuốc
     │
     ▼
   ┌──────────────────┐
   │ 1. YOLO Detect   │  models/yolo/best.pt (6MB)
   │    crop vùng đơn  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 2. Preprocess    │  deskew + orientation AI
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 3. OCR           │  PaddleOCR detect + VietOCR recognize
   │    → text blocks  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 4. NER Classify  │  models/phobert_ner_model/ (PhoBERT)
   │    drugname/other │
   └──────────────────┘
          ▼
   📋 Danh sách thuốc

 PHASE B: XÁC MINH THUỐC (chưa hoạt động)
 ──────────────────────────────────────────
   ⚠️ Code có sẵn nhưng chưa functional.
   Dùng Zero-PIMA: FRCNN detect pills + GCN match.
   Cần patched roi_heads.py để chạy contrastive matching.
```

## Code Mapping

| Step | Module | Code Path | Status |
|------|--------|-----------|--------|
| 1 | YOLO Detect | `core/phase_a/s1_detect/` | ✅ |
| 2 | Preprocess | `core/phase_a/s2_preprocess/` | ✅ |
| 3 | OCR | `core/phase_a/s3_ocr/` | ✅ |
| 4 | NER Classify | `core/phase_a/s5_classify/ner_extractor.py` | ✅ |
| — | Drug Search | `core/phase_a/s6_drug_search/` | ✅ (available) |

## Model Weights

| File | Size | Mô tả |
|------|------|-------|
| `models/yolo/best.pt` | 6MB | YOLO11n-seg — detect vùng đơn thuốc |
| `models/phobert_ner_model/` | ~500MB | PhoBERT NER — classify drugname/other |
| `models/zero_pima/zero_pima_best.pth` | 521MB | Phase B only — FRCNN + GCN match |

## Hiệu Suất (Phase A)

| Stage | Thời gian | Ghi chú |
|-------|-----------|---------|
| YOLO detect+crop | ~2s | best.pt (6MB), fallback to full image nếu fail |
| Preprocess | <1s | Deskew + Portrait rotation (AI orientation skipped) |
| OCR (Hybrid) | ~5s | PaddleOCR detect + VietOCR recognize (perspective crop) |
| NER classify | ~1s | PhoBERT model |
| **Tổng (warm)** | **~7s** | Sau warm-up |
| **Tổng (cold)** | **~17s** | Ảnh đầu tiên (model loading) |

### Benchmark toàn bộ (2026-03-10)

| Chỉ số | Kết quả |
|--------|---------|
| Tổng ảnh | 50/50 ✅ |
| Tổng drugs detected | 338 |
| Avg drugs/ảnh | 6.8 |
| Errors | 0 |
| Ảnh 0 drugs | 0 |
| IMG_180633 (bug cũ 0 drugs) | 1 drug |

### Kết quả test trên prescription_3:
- **5/5 thuốc** nhận diện đúng (97% confidence)
- **0 false positives**
- Celecoxib, Eperisone, Mecobalamin, Loratadine, Paracetamol

## CLI Commands

```bash
# Chạy 1 ảnh
python scripts/run_pipeline.py --image data/input/IMG_XXX.jpg

# Chạy 1 folder ảnh
python scripts/run_pipeline.py --dir data/input/prescription_3

# Chạy tất cả
python scripts/run_pipeline.py --all

# Giới hạn số ảnh
python scripts/run_pipeline.py --all --limit 5

# Bỏ qua NER (fallback)
python scripts/run_pipeline.py --all --no-ner
```

## Output Structure

```
data/output/phase_a/<tên_ảnh>/
├── summary.json               ← Tổng hợp kết quả + danh sách thuốc
├── step-0_raw.jpg             ← Ảnh gốc
├── step-1_cropped.jpg         ← Ảnh sau YOLO crop
├── step-2_preprocessed.jpg    ← Ảnh sau preprocess
├── step-3_ocr.json            ← Kết quả OCR (text blocks)
├── step-3.txt                 ← OCR text thuần
└── step-4_ner_classify.json   ← Kết quả NER (drugname/other)
```

## Archived (không còn sử dụng)

Đã chuyển vào `archive/deprecated_gcn/`:
- `gcn_classifier.py` — GCN classify cũ (thay bằng PhoBERT NER)
- `evaluate.py` — Script đánh giá GCN
- `s4_grouping/` — Module merge text blocks (NER xử lý trực tiếp OCR output)

# MedicineApp Pipeline — Tài Liệu Kỹ Thuật

> Last updated: 2026-03-14

## Kiến Trúc Tổng Quan

```
 PHASE A: QUÉT ĐƠN THUỐC (5 bước)
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
   │ 2. Preprocess    │  Deskew + AI orientation (PP-LCNet)
   │                  │  ⚠️ KHÔNG dùng force_portrait() — bug xoay sai YOLO-crop
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 2.1 Quality Gate │  GOOD / WARNING / REJECT
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 2.2 Table ROI    │  models/yolo/table_best.pt (optional)
   │     YOLO detect   │  fallback full-image OCR nếu fail
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 3. OCR           │  PaddleOCR detect + VietOCR recognize
   │    → text blocks  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 3.5 merge_lines  │  Gộp OCR blocks cùng dòng Y-axis
   │    → 1 block/dòng │  VD: 29 blocks → 13 dòng
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 4. NER Classify  │  models/phobert_ner_model/ (PhoBERT)
   │    drugname/other │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 5. Drug Search   │  drug_db_vn_full.json (9,284 thuốc)
   │    fuzzy-match    │  tenThuoc + hoatChat (generic)
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
| 2.1 | Quality Gate | `core/phase_a/s2_preprocess/quality_gate.py` | ✅ |
| 2.2 | Table ROI YOLO | `core/pipeline.py::_detect_table_roi` | ✅ (optional) |
| 3 | OCR | `core/phase_a/s3_ocr/` | ✅ |
| 3.5 | **merge_into_lines()** | `core/phase_a/s3_ocr/ocr_engine.py` | ✅ |
| 4 | NER Classify | `core/phase_a/s5_classify/ner_extractor.py` | ✅ |
| 5 | **Drug Search** | `core/phase_a/s6_drug_search/drug_lookup.py` | ✅ (9,284 thuốc) |

## Model Weights

| File | Size | Mô tả |
|------|------|-------|
| `models/yolo/best.pt` | varies | YOLO11n-seg — detect vùng đơn thuốc |
| `models/yolo/table_best.pt` | varies | YOLO11n-seg — detect bảng thuốc (ROI OCR) |
| `models/phobert_ner_model/` | ~500MB | PhoBERT NER — classify drugname/other |
| `models/zero_pima/zero_pima_best.pth` | 521MB | Phase B only — FRCNN + GCN match |

## Output Semantics (Phase A)

- `medications`: danh sách thuốc dùng downstream, gồm cả `confirmed` và `unmapped_candidate`.
- `medication_candidates`: tất cả candidate với `mapping_status` rõ ràng:
       - `confirmed`
       - `unmapped_candidate`
       - `rejected_noise`
- ROI metadata:
       - `roi_mode`: `table_roi` hoặc `full_image`
       - `roi_bbox`, `roi_offset`
- Quality metadata:
       - `quality_state`, `reject_reason`, `guidance`, `quality_metrics`

## Hiệu Suất (Phase A)

| Stage | Thời gian | Ghi chú |
|-------|-----------|---------|
| YOLO detect+crop | ~2s | best.pt (6MB), fallback to full image nếu fail |
| Preprocess | <1s | Deskew + AI orientation (PP-LCNet 0°/90°/180°/270°) — **bỏ force_portrait()** |
| OCR (Hybrid) | ~5s | PaddleOCR detect + VietOCR recognize (perspective crop) |
| merge_into_lines | <0.1s | Gộp blocks cùng dòng Y-axis (VD: 29→13) |
| NER classify | ~1s | PhoBERT model |
| Drug Search | ~0.1s | Fuzzy match 9,284 thuốc (rapidfuzz) |
| **Tổng (warm)** | **~8s** | Sau warm-up |
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

### Adaptive ROI smoke benchmark (2026-03-14)

- Thiết lập: so sánh `roi_on` (YOLO table ROI bật) vs `roi_off` (full-image OCR) trên 8 ảnh sample từ `data/input`.
- Kết quả nhanh:
       - `roi_on`: avg ~1.61s/ảnh, ROI thực sự được dùng 1/8 ảnh, tổng confirmed=2, unmapped=1.
       - `roi_off`: avg ~1.75s/ảnh, tổng confirmed=4, unmapped=3.
- Kết luận hiện tại:
       - ROI có thể giúp giảm latency ở ảnh trúng ROI.
       - Nhưng chưa đủ ổn định để bật như chiến lược tối ưu mặc định vì có dấu hiệu giảm recall ở sample này.
       - Tiếp tục giữ fallback full-image OCR và cần benchmark lớn hơn trước khi chốt policy mặc định.

### Kết quả test trên prescription_3 (sau fix 2026-03-14):

| Chỉ số | Trước fix | Sau fix |
|--------|----------|---------|
| OCR blocks | 27 ký tự đơn | 29 raw → **13 dòng** hoàn chỉnh |
| NER drugs | **0** | **5** |
| Drug Search | — | **5/5** tìm thấy (9,284 thuốc) |
| Thời gian | 8.4s | 9.0s (+0.6s cho AI orient + drug search) |

Các thuốc được nhận diện đúng: Celecoxib, Eperisone, Mecobalamin, Loratadine, Paracetamol

**Root cause bug:** `force_portrait()` xoay 90° ảnh YOLO-crop landscape (1961×1181) → chữ nằm ngang → OCR sai.
**Fix:** Bỏ `force_portrait()`, dùng AI orientation `fix_orientation_ai()` với `skip_ai_fix=False`.

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
├── step-3_ocr.json            ← Kết quả OCR (text blocks) + raw_block_count
├── step-3.txt                 ← OCR text thuần
├── step-4_ner_classify.json   ← Kết quả NER labeled (drugname/other)
└── step-5_drug_search.json   ← ★ Drug search: tên chuẩn DB 9,284 thuốc
```

## Archived (không còn sử dụng)

Đã chuyển vào `archive/deprecated_gcn/`:
- `gcn_classifier.py` — GCN classify cũ (thay bằng PhoBERT NER)
- `evaluate.py` — Script đánh giá GCN
- `s4_grouping/` — Module merge text blocks (NER xử lý trực tiếp OCR output)

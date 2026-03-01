# MedicineApp Pipeline Status

> Last updated: 2026-02-27 22:25

## Architecture — 2-Phase Pipeline

```
 PHASE A: QUÉT ĐƠN THUỐC
 ────────────────────────
   📷 Ảnh đơn thuốc
     │
     ▼
   ┌──────────────────┐
   │ 1. YOLO Detect   │  best.pt (6MB)
   │    crop vùng đơn  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 2. Preprocess    │  deskew + orientation AI
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 3. OCR           │  PaddleOCR + VietOCR
   │    → text blocks  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 4. Grouping      │  merge + group drug lines
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 5. GCN Classify  │  zero_pima_best.pth (model_match)
   │    drugname/other │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 6. Drug Search   │  fuzzy match drug_db_vn.csv
   │    → drug info    │
   └──────────────────┘
          ▼
   📋 Lập lịch uống thuốc

 PHASE B: XÁC MINH THUỐC (khi uống)
 ────────────────────────────────────
   📷 Ảnh viên thuốc + đơn đã quét
     │
     ▼
   ┌──────────────────┐
   │ 7. FRCNN Detect  │  zero_pima_best.pth (model_loc)
   │    → pill bboxes  │
   └──────┬───────────┘
          ▼
   ┌──────────────────┐
   │ 8. GCN Match     │  zero_pima_best.pth (full)
   │    pill ↔ drug    │
   └──────────────────┘
          ▼
   ✅/❌ Đúng thuốc hay không
```

## Model Weights

| File | Size | Chứa gì |
|------|------|---------|
| `models/weights/best.pt` | 6MB | YOLO11n-seg (detect vùng đơn thuốc) |
| `models/weights/zero_pima_best.pth` | 521MB | FRCNN (model_loc) + GCN (model_match) |

## Zero-PIMA Training (Completed ✅)

| Epoch | Loss | Ghi chú |
|-------|------|---------|
| 19 | 1.9643 | Start of final training run |
| 25 | 1.8507 | |
| 30 | 1.7986 | |
| 35 | 1.7528 | |
| 40 | 1.7275 | |
| 45 | 1.7145 | |
| 50 | **1.6923** | 💾 **Final best** — `zero_pima_best.pth` |

> Training: 50 epochs, ~7m18s/epoch, Colab Pro L4 GPU.

## Performance (Phase A)

| Stage | Time (CPU) | Note |
|---|---|---|
| YOLO detect+crop | ~1s | best.pt (6MB) |
| Preprocess | ~7s | Singleton classifier |
| OCR (Hybrid) | ~25s | PaddleOCR + VietOCR |
| Grouping | <0.1s | — |
| GCN classify | ~2s | GPU, first load ~5s |
| Drug search | <0.1s | Local VN DB |
| **Total** | **~35s** | |

## Scripts

```bash
# Unified pipeline (Phase A)
python scripts/run_pipeline.py --image data/input/IMG_XXX.jpg

# Batch all images
python scripts/run_pipeline.py --all

# Legacy: debug pipeline
python scripts/run_debug_pipeline.py

# Legacy: batch pipeline (step 1-5 only)
python scripts/run_batch_pipeline.py
```

---
description: how to run the Phase A pipeline on images
---

# Run Pipeline (Phase A)

## Chuẩn bị
// turbo
1. Activate venv: `source venv/bin/activate`

## Chạy

// turbo
2. Chạy 1 ảnh (test nhanh — AI có thể auto-run):
```bash
python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg
```

3. Chạy 1 folder ảnh — **CONFIRM VỚI USER TRƯỚC KHI CHẠY**:
```bash
python scripts/run_pipeline.py --dir data/input/prescription_3
```

4. Chạy tất cả 51 ảnh (~6 phút) — **CHỈ CHẠY KHI USER YÊU CẦU RÕ RÀNG**:
```bash
python scripts/run_pipeline.py --all
```

5. Chạy batch nhỏ để test:
// turbo
```bash
python scripts/run_pipeline.py --all --limit 3
```

## Kết quả
6. Output nằm tại `data/output/phase_a/<tên_ảnh>/`
   - `summary.json` — kết quả cuối (list thuốc + timing)
   - `step-3_ocr.json` — OCR text blocks thô
   - `step-4_ner_classify.json` — NER labels

## Hiệu suất
- Cold start (ảnh đầu tiên): ~13s
- Warm (các ảnh sau): ~6-7s/ảnh
- Kỳ vọng: 5-13 thuốc/ảnh tùy đơn

> ⚠️ **Lưu ý:** Chạy `--all` sẽ ghi đè output cũ. Backup thư mục `data/output/` nếu cần giữ kết quả trước đó.

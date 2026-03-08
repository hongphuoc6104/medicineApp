---
description: how to debug when pipeline gives wrong results (0 drugs, text rác, slow)
---

# Debug Pipeline

## Bước 1: Xem log real-time

// turbo
1. Chạy pipeline với log đầy đủ (stderr hiện ra màn hình):
```bash
python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg 2>&1 | tee /tmp/pipeline_debug.log
```

## Bước 2: Xem output từng bước

2. Mở folder output: `data/output/phase_a/<tên_ảnh>/`

| File | Kiểm tra gì | Dấu hiệu lỗi |
|------|-------------|---------------|
| `step-1_cropped.jpg` | YOLO crop đúng vùng đơn? | Ảnh bị cắt quá nhỏ hoặc trống |
| `step-2_preprocessed.jpg` | Ảnh có bị xoay sai? | Chữ bị lộn ngược |
| `step-3_ocr.json` | OCR đọc được text? | Mảng rỗng hoặc text rác |
| `step-4_ner_classify.json` | NER label đúng? | Tất cả là `"other"`, 0 `"drugname"` |

// turbo
3. Xem nhanh nội dung summary:
```bash
cat data/output/phase_a/$(ls data/output/phase_a/ | tail -1)/summary.json | python -m json.tool
```

## Bước 3: Fix theo triệu chứng

### Triệu chứng: 0 thuốc (0 drugs)
// turbo
4. Kiểm tra ngưỡng confidence YOLO:
```bash
grep "CONF_THRESHOLD" core/config.py
```
- Nếu `CONF_THRESHOLD = 0.90` quá cao → thử giảm xuống `0.70` trong `core/config.py`

### Triệu chứng: Text rác (chữ ghép nhầm)
5. Nguyên nhân: `_crop_polygon()` trong `core/phase_a/s3_ocr/ocr_engine.py` đang dùng `cv2.boundingRect()`.
   - **Known issue** — chưa fix. Giải pháp: dùng `cv2.getPerspectiveTransform()`.

### Triệu chứng: Chậm bất thường (>20s/ảnh)
// turbo
6. Kiểm tra GPU:
```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); import paddle; print('Paddle GPU:', paddle.device.cuda.device_count())"
```
- Nếu CUDA: `False` → đang chạy CPU, rất chậm
- PaddleOCR load thêm model recognition (+2-3s) — giới hạn API không tắt được

## Bước 4: Chạy lại ảnh lỗi
// turbo
7. Chạy riêng ảnh có vấn đề:
```bash
python scripts/run_pipeline.py --image data/input/<folder>/<tên_ảnh>.jpg
```

## Known Bugs chưa fix
| Bug | Ảnh | Triệu chứng | Nghi ngờ |
|-----|-----|-------------|---------|
| 0 drugs | `IMG_20260209_180633` | 2.7s, 0 thuốc | YOLO crop trượt |
| Text rác | ảnh chữ cong | Chữ bị ghép nhầm | `cv2.boundingRect()` |

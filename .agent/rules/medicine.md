# Project Rules - Medicine App

## Tech Stack & Versions (KHÔNG ĐƯỢC THAY ĐỔI trừ khi user yêu cầu)

- Python 3.12.3
- PyTorch 2.10.0 / torchvision 0.25.0
- PaddleOCR 3.4.0 / PaddlePaddle 3.3.0
- VietOCR 0.3.13
- FastAPI 0.134.0 / Uvicorn 0.41.0
- Ultralytics (YOLO) 8.4.14
- torch-geometric 2.7.0
- transformers 5.2.0
- OpenCV 4.10.0
- NumPy 2.4.2
- GPU: NVIDIA GeForce RTX 3050 Laptop

---

## Ràng buộc quan trọng (PHẢI TUÂN THỦ)

### 1. OCR Pipeline
- **Text Detection**: PaddleOCR 3.4.0 (chỉ dùng detect, KHÔNG dùng recognize)
- **Text Recognition**: VietOCR 0.3.13 (đọc chữ Việt chính xác hơn)
- Pipeline: `PaddleOCR detect → VietOCR recognize`
- Module chính: `core/ocr/ocr_engine.py` → `HybridOcrModule`
- KHÔNG dùng PaddleOCR thuần cho cả detect + recognize

### 2. PaddleOCR 3.4.0 API (ĐÃ THAY ĐỔI so với v2)
- ❌ `use_gpu` → Tự động detect, dùng `device='gpu'/'cpu'`
- ❌ `show_log` → Không còn tồn tại
- ❌ `use_angle_cls` → Đổi thành `use_textline_orientation`
- ❌ `ocr(img, cls=True)` → Dùng `ocr(img)` hoặc `predict(img)`
- ✅ Params hợp lệ: `lang`, `device`, `use_textline_orientation`, `text_det_thresh`, `text_det_box_thresh`, `text_det_limit_side_len`

### 3. Model Weights
- YOLO: `models/weights/best.pt` (5.8MB)
- Zero-PIMA: `models/weights/zero_pima_best.pth` (~654MB)
- Checkpoint keys (Colab training): `model_loc`, `model_match`, `epoch`, `best_loss`

### 4. Zero-PIMA Training (Colab)
- Checkpoint upload HuggingFace mỗi epoch
- Best model chỉ lưu khi loss < best_loss cũ
- `zero_pima_checkpoint.pth` = checkpoint mới nhất (luôn có trên HF)
- Resume: load checkpoint → `START_EPOCH = ckpt['epoch'] + 1`

### 5. Drug Data Sources
- Local: `data/drug_db.json` (107 thuốc VAIPE, có color + shape)
- DDI Lab VN API: `ddi.lab.io.vn` (1,854 thuốc VN, có shape 85%)
- Online: OpenFDA, RxNorm, DailyMed (tra real-time)

---

## Các lỗi đã gặp (TRÁNH LẶP LẠI)

### Lỗi 1: PaddleOCR API changed
- **Nguyên nhân**: PaddleOCR v3.4+ thay đổi API hoàn toàn so với v2
- **Biểu hiện**: `ValueError: Unknown argument: use_gpu/show_log`
- **Fix**: Dùng HybridOcrModule trong `core/ocr/ocr_engine.py`

### Lỗi 2: Checkpoint key mismatch
- **Nguyên nhân**: Colab notebook lưu `model_loc`/`model_match`, matcher.py expect khác
- **Fix**: Auto-detect keys trong `core/matcher.py`

### Lỗi 3: PaddlePaddle MKLDNN bug
- **Nguyên nhân**: PaddlePaddle 3.3.0
- **Fix**: `os.environ.setdefault("FLAGS_enable_pir_api", "0")`

### Lỗi 4: Port 8000 already in use
- **Fix**: `fuser -k 8000/tcp` trước khi restart server

### Lỗi 5: Colab disconnect mất dữ liệu
- **Fix**: Upload checkpoint lên HuggingFace Hub mỗi epoch

---

## Cấu trúc Project

```
medicineApp/
├── core/                  # Core logic
│   ├── pipeline.py        # Main pipeline orchestrator
│   ├── matcher.py         # Zero-PIMA wrapper
│   ├── detector.py        # YOLO prescription detector
│   ├── pill_detector.py   # FRCNN pill detector
│   ├── ocr/
│   │   ├── ocr_engine.py  # HybridOCR (PaddleOCR det + VietOCR rec)
│   │   └── base.py        # Base OCR classes
│   └── converter/
│       └── drug_lookup.py # Drug name mapper
├── server/
│   ├── main.py            # FastAPI server
│   └── services/
│       └── drug_service.py # Drug info API
├── models/weights/         # Model weights
├── Zero-PIMA/              # Training code
├── data/                   # Input images & drug DB
└── scripts/                # Utility scripts
```

---

*Cập nhật: 01/03/2026*
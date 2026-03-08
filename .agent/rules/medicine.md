# Project Rules — MedicineApp

## Tech Stack (KHÔNG THAY ĐỔI trừ khi user yêu cầu)

- Python 3.12.3
- PyTorch 2.10.0 / torchvision 0.25.0
- PaddleOCR 3.4.0 / PaddlePaddle 3.3.0
- VietOCR 0.3.13
- FastAPI 0.134.0 / Uvicorn 0.41.0
- Ultralytics (YOLO) 8.4.14
- transformers 5.2.0
- OpenCV 4.10.0
- GPU: NVIDIA GeForce RTX 3050 4GB

---

## Quy tắc Bắt buộc

### 1. Pipeline Phase A = 4 bước
```
YOLO detect → Preprocess → Hybrid OCR → PhoBERT NER
```
- ❌ KHÔNG đề xuất dùng GCN cho Phase A (đã bỏ, archive ở `archive/deprecated_gcn/`)
- ❌ KHÔNG tạo lại module `s4_grouping` (đã bỏ, NER xử lý trực tiếp OCR output)
- ❌ KHÔNG import `GcnClassifier` — đã thay hoàn toàn bằng `NerExtractor`

### 2. Đường dẫn CHÍNH XÁC (đã refactor)
```
core/phase_a/s1_detect/          # YOLO crop
core/phase_a/s2_preprocess/      # Deskew
core/phase_a/s3_ocr/ocr_engine.py  # HybridOcrModule
core/phase_a/s5_classify/ner_extractor.py  # NerExtractor
core/phase_a/s6_drug_search/     # Drug fuzzy lookup
core/config.py                   # CONF_THRESHOLD=0.90, paths
core/pipeline.py                 # API orchestrator
scripts/run_pipeline.py          # CLI chính
```

### 3. Model Weights
```
models/yolo/best.pt              # 6MB — YOLO detect
models/phobert_ner_model/        # ~500MB — PhoBERT NER
models/zero_pima/zero_pima_best.pth  # 521MB — Phase B only
```

### 4. OCR Pipeline
- **Detection**: PaddleOCR 3.4.0 (`device='gpu'`) — chỉ dùng detect
- **Recognition**: VietOCR 0.3.13 (`device='cuda'`) — đọc chữ Việt
- KHÔNG dùng PaddleOCR cho cả detect + recognize

### 5. PaddleOCR 3.4.0 API (khác v2)
- ❌ `use_gpu` → dùng `device='gpu'/'cpu'`
- ❌ `show_log` → không còn
- ❌ `use_angle_cls` → dùng `use_textline_orientation`
- ❌ `ocr(img, cls=True)` → dùng `ocr(img)` hoặc `predict(img)`

### 6. Phase B — KHÔNG SỬA
- `core/phase_b/` và `Zero-PIMA/` đang HOLD
- Trừ khi user bảo "làm Phase B", bỏ qua hoàn toàn

### 7. Data
- Drug DB: `data/drug_db_vn.csv` (KHÔNG phải `drug_db.json`)
- Input: `data/input/` (7 folders, 51 ảnh)
- Output: `data/output/phase_a/<tên_ảnh>/`

### 8. BẮT BUỘC CHO MỌI AI AGENT MỚI
- ⚠️ Nếu bạn là một AI mới tinh, bạn **PHẢI** đọc file `AGENTS.md` ở thư mục gốc trước khi viết bất kỳ dòng code nào. File đó chứa ngữ cảnh, roadmap và giải thích lý do các thành phần bị xóa.

### 9. Python Coding Convention
- Tuân thủ PEP8, dùng Type hints (typing) cho mọi hàm.
- Luôn viết Docstring (mô tả hàm, args, returns).
- Dùng **absolute imports** cho nội bộ dự án (VD: `from core.phase_a.s1_detect.detector import Detector` thay vì `from .detector import Detector`).

### 10. Git Safety Rules
- ❌ KHÔNG commit thư mục `models/` (file weights >500MB — đã có trong `.gitignore`)
- ❌ KHÔNG commit thư mục `data/output/` hay `venv/`
- ❌ KHÔNG push thẳng vào nhánh `main` — tạo branch mới nếu cần
- ✅ Trước khi commit: chạy `git status` để kiểm tra file sẽ được stage
- ✅ Kiểm tra `.gitignore` tại root nếu nghi ngờ file có bị track không

---

## Lỗi Đã Gặp (TRÁNH LẶP LẠI)

### PaddleOCR API changed (v3.4 vs v2)
- Fix: Dùng `HybridOcrModule` trong `core/phase_a/s3_ocr/ocr_engine.py`

### PaddlePaddle MKLDNN bug
- Fix: `os.environ.setdefault("FLAGS_enable_pir_api", "0")`

### Port 8000 in use
- Fix: `fuser -k 8000/tcp`

---

*Cập nhật: 08/03/2026*
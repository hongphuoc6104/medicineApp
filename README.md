# MedicineApp

> AI-powered prescription scanning and medication extraction
> Hệ thống AI hỗ trợ quét đơn thuốc và trích xuất danh sách thuốc

[![Phase A](https://img.shields.io/badge/Phase_A-Active-brightgreen)](#current-status)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

MedicineApp turns a prescription photo into structured medication data.
MedicineApp biến ảnh đơn thuốc thành dữ liệu có cấu trúc để hỗ trợ tra cứu, lưu trữ và tích hợp với ứng dụng di động.

The public repository focuses on Phase A, the prescription-scanning flow that is already working end to end.
Kho lưu trữ công khai tập trung vào Phase A, tức luồng quét đơn thuốc đã chạy được từ đầu đến cuối.

Phase B for pill verification is intentionally on hold.
Phase B dùng để xác minh viên thuốc hiện đang tạm dừng.

## What it solves / Bài toán giải quyết

- Manual prescription transcription is slow and error-prone. Đọc tay đơn thuốc dễ sai, chậm và khó đồng nhất.
- MedicineApp automates crop, OCR, NER, and drug lookup for Vietnamese prescriptions. MedicineApp tự động cắt vùng đơn thuốc, OCR, NER và tra cứu tên thuốc cho đơn tiếng Việt.

## Highlights / Điểm nổi bật

- YOLO-based prescription detection with convex-hull cropping. Phát hiện vùng đơn thuốc bằng YOLO và cắt theo convex hull để giữ nội dung bên trong.
- Deskew and orientation normalization for rotated photos. Nắn ảnh lệch góc và chuẩn hóa chiều xoay cho ảnh chụp thực tế.
- Hybrid OCR with PaddleOCR detection and VietOCR recognition. OCR lai: PaddleOCR để phát hiện vùng chữ và VietOCR để nhận dạng tiếng Việt.
- PhoBERT NER for drug-name extraction. PhoBERT NER để trích xuất tên thuốc.
- Fuzzy lookup against `data/drug_db_vn_full.json` with 9,284 Vietnamese drug records. Tra cứu gần đúng trên `data/drug_db_vn_full.json` với 9,284 thuốc Việt Nam.
- CLI, FastAPI service, and Node.js backend support the same project. CLI, dịch vụ FastAPI và backend Node.js cùng phục vụ cho một hệ thống thống nhất.

<a id="current-status"></a>
## Current status / Trạng thái hiện tại

| English | Tiếng Việt |
|---|---|
| Phase A is active and usable. | Phase A đang hoạt động và có thể dùng được. |
| Phase B is on hold. | Phase B hiện tạm dừng. |
| Main output: `data/output/phase_a/<image>/summary.json`. | Output chính: `data/output/phase_a/<image>/summary.json`. |
| Current benchmark: 50/50 test images processed successfully, 338 drugs extracted, 0 errors. | Benchmark hiện tại: xử lý thành công 50/50 ảnh test, trích xuất 338 thuốc, 0 lỗi. |
| NER result: 100% F1 on the test set. | NER đạt F1 100% trên tập test. |

## Pipeline / Quy trình

1. Detect and crop the prescription region. Phát hiện và cắt vùng đơn thuốc.
2. Preprocess the image with deskew and auto-orientation. Tiền xử lý ảnh với deskew và xoay tự động.
3. Run hybrid OCR to extract text blocks. Chạy OCR lai để lấy các block văn bản.
4. Classify drug names with PhoBERT NER. Phân loại tên thuốc bằng PhoBERT NER.
5. Fuzzy-match names against the Vietnamese drug database. So khớp gần đúng với cơ sở dữ liệu thuốc Việt Nam.

## Tech stack / Công nghệ

| Component | Role |
|---|---|
| Python 3.12 | AI pipeline and CLI |
| FastAPI | Python AI service |
| Node.js / Express | Main backend API |
| PostgreSQL 16 | Database and sessions |
| Flutter | Mobile client |
| YOLOv11n-seg | Prescription detection |
| PaddleOCR | Text detection |
| VietOCR | Text recognition |
| PhoBERT-base-v2 | NER model |

## Setup / Cài đặt

```bash
git clone git@github.com:hongphuoc6104/medicineApp.git
cd medicineApp

python3.12 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Model weights / Trọng số mô hình

| Model | Path | Note |
|---|---|---|
| YOLO detect | `models/yolo/best.pt` | Prescription crop model |
| PhoBERT NER | `models/phobert_ner_model/` | NER weights |
| Zero-PIMA | `models/zero_pima/zero_pima_best.pth` | Phase B only |

## Usage / Cách sử dụng

### CLI

```bash
source venv/bin/activate

python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg
python scripts/run_pipeline.py --dir data/input/prescription_3
python scripts/run_pipeline.py --all
```

### FastAPI AI service

```bash
source venv/bin/activate
python -m server.main
```

### Node.js backend

```bash
cd server-node
npm install
npm run dev
```

## Project structure / Cấu trúc dự án

```
medicineApp/
├── core/           # AI pipeline source
├── scripts/        # CLI and training scripts
├── server/         # FastAPI AI service
├── server-node/    # Node.js main backend
├── mobile/         # Flutter client
├── models/         # Model weights
├── data/           # Inputs, outputs, datasets
├── tests/          # Python tests
└── archive/        # Deprecated or superseded work
```

## License / Giấy phép

MIT License. See [`LICENSE`](LICENSE).

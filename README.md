# MedicineApp

He thong AI ho tro quet don thuoc va xac minh vien thuoc.

> **Trang thai**: Phase A (quet don thuoc) da hoat dong. Phase B (xac minh vien thuoc) dang hold.

---

## Tinh nang

### Phase A - Quet don thuoc (Hoat dong)
Chup anh don thuoc -> nhan dien danh sach ten thuoc tu dong.

### Phase B - Xac minh vien thuoc (Hold)
Chup anh vien thuoc -> so khop voi don thuoc da quet.

---

## Pipeline Phase A - 4 buoc

```
Anh don thuoc
  -> [1] YOLO Detect and Crop    - Cat vung don thuoc
  -> [2] Preprocess               - Deskew, xoay phang
  -> [3] Hybrid OCR               - PaddleOCR detect + VietOCR recognize
  -> [4] PhoBERT NER Classify     - Nhan dien ten thuoc (drugname/other)
  -> JSON danh sach thuoc
```

---

## Cai dat

```bash
# Clone repo
git clone git@github.com:hongphuoc6104/medicineApp.git
cd medicineApp

# Tao virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Cai dependencies
pip install -r requirements.txt
```

### Download Model Weights (khong co trong repo)

| Model | Duong dan | Kich thuoc |
|-------|----------|-----------|
| YOLO detect | `models/yolo/best.pt` | 6MB |
| PhoBERT NER | `models/phobert_ner_model/` | ~500MB |
| Zero-PIMA (Phase B) | `models/zero_pima/zero_pima_best.pth` | 521MB |

---

## Su dung

### CLI - Chay Pipeline

```bash
source venv/bin/activate

# 1 anh
python scripts/run_pipeline.py --image data/input/prescription_3/IMG_20260209_180505.jpg

# 1 folder
python scripts/run_pipeline.py --dir data/input/prescription_3

# Tat ca anh
python scripts/run_pipeline.py --all
```

### FastAPI Server

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8100
# -> http://localhost:8100
# -> Swagger docs: http://localhost:8100/docs
```

**Endpoints chinh:**

| Endpoint | Method | Mo ta |
|----------|--------|-------|
| `/api/health` | GET | Kiem tra trang thai server |
| `/api/scan-prescription` | POST | Upload anh don thuoc -> nhan dien thuoc |
| `/api/drugs` | GET | Tim kiem DB thuoc local |
| `/api/drug-info/{name}` | GET | Thong tin chi tiet 1 thuoc |
| `/api/drugs/search-vn` | GET | Tim thuoc VN qua DDI Lab API |

---

## Mobile Dev Khong Phu Thuoc Wi-Fi

Khi test app Android that, khuyen nghi dung USB + `adb reverse` thay vi hardcode IP LAN.

```bash
bash dev.sh
cd mobile && flutter run -d <device-id>
```

Workflow nay se cap nhat `mobile/.env` ve:

```bash
API_BASE_URL=http://127.0.0.1:3101/api
```

va map request tren dien thoai ve may dev qua USB. `dev.sh` chay:

- PostgreSQL bang Docker
- Node API local tren `3101`
- Python AI local tren `8100`

nen khong can sua lai IP moi lan doi Wi-Fi.

---

## Cau truc du an

```
medicineApp/
├── core/                        # Source code chinh
│   ├── phase_a/                 #   Pipeline 4 buoc
│   │   ├── s1_detect/           #     YOLO crop
│   │   ├── s2_preprocess/       #     Deskew + orientation
│   │   ├── s3_ocr/              #     PaddleOCR + VietOCR
│   │   ├── s5_classify/         #     PhoBERT NER
│   │   └── s6_drug_search/      #     Drug fuzzy lookup
│   ├── phase_b/                 #   [HOLD] Xac minh vien thuoc
│   ├── config.py                #   Cau hinh (thresholds, paths)
│   └── pipeline.py              #   API orchestrator
├── scripts/                     #   CLI scripts
├── server/                      #   FastAPI server
├── models/                      #   Model weights (khong commit)
├── data/                        #   Input/output data
├── docs/                        #   Tai lieu chi tiet
├── archive/                     #   Code cu da bo
├── AGENTS.md                    #   Onboarding guide cho AI agents
└── PIPELINE_STATUS.md           #   Tai lieu ky thuat pipeline
```

---

## Tech Stack

| Component | Chi tiet |
|-----------|---------|
| Python | 3.12 |
| OCR Detection | PaddleOCR PP-OCRv5 (GPU) |
| OCR Recognition | VietOCR vgg_transformer (CUDA) |
| NER | PhoBERT-base-v2 fine-tuned (BIO tagging) |
| Object Detection | YOLOv11n-seg |
| Server | FastAPI |
| GPU | NVIDIA RTX 3050 4GB |

---

## Hieu suat

| Metric | Gia tri |
|--------|--------|
| Cold start | ~13s/anh (loading models) |
| Warm inference | ~6-7s/anh |
| NER F1-score | 100% (test set) |

---

## Tai lieu

- [AGENTS.md](AGENTS.md) - Onboarding guide cho AI agents
- [PIPELINE_STATUS.md](PIPELINE_STATUS.md) - Chi tiet ky thuat pipeline
- [docs/project_status.md](docs/project_status.md) - Tien do du an
- [docs/master_plan.md](docs/master_plan.md) - Master plan thiet ke

---

## License

MIT License - xem file [LICENSE](LICENSE).

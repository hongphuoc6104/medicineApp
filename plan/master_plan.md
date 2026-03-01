# MedicineApp — Master Plan

## 1. Tổng Quan Dự Án

### 1.1 Mô tả
Ứng dụng hỗ trợ bệnh nhân quản lý thuốc từ đơn thuốc bệnh viện. AI quét đơn thuốc → trích xuất tên thuốc → lập lịch nhắc uống → quét viên thuốc thật để xác minh đúng thuốc trước khi uống.

### 1.2 Người dùng mục tiêu
Bất kỳ ai lĩnh thuốc tại bệnh viện — không yêu cầu kiến thức kỹ thuật. Giao diện đơn giản, trực quan.

### 1.3 Kiến trúc tổng thể

```
┌──────────────────┐        WiFi/API         ┌──────────────────────────┐
│  Flutter App     │ ◄──────────────────────► │  Python FastAPI Server   │
│  (Android)       │    REST API (JSON)       │  (PC của bạn)            │
│                  │                          │                          │
│  - Camera chụp   │    POST /scan-rx         │  - YOLO detect đơn thuốc │
│  - Lịch nhắc     │    POST /scan-pills      │  - PaddleOCR đọc text    │
│  - Xác nhận uống │    GET  /drug-info       │  - GCN phân loại tên     │
│  - SQLite local  │                          │  - Zero-PIMA matching    │
│  - Notification  │                          │  - Drug info lookup      │
└──────────────────┘                          └──────────────────────────┘
```

### 1.4 Luồng sử dụng chính

**Luồng A — Scan & Lập lịch:**
```
[Mở App]
  │
  ├── 📷 Quét (Camera) ──────────────────────────────────────────
  │       → Chụp 1 ảnh → gửi → xử lý
  │       → Hoặc: chụp 2-3 ảnh cùng đơn → multi-frame fusion → xử lý
  │
  └── 🖼️ Chọn từ thư viện ──────────────────────────────────────
          → Chọn 1 ảnh → gửi → xử lý
          → Chọn 2-3 ảnh → popup:
              "Đây là cùng 1 toa thuốc (chụp nhiều góc)?"
              [✅ Cùng 1 toa — Gộp lại] → multi-frame fusion → xử lý
              [❌ Đóng — Quét từng toa] → user quay lại scan lần lượt

Sau khi có ảnh (camera hoặc gallery):
→ [Gửi ảnh → FastAPI]
→ [YOLO crop đơn] → [Preprocessing xoay/chỉnh] → [OCR đọc text+bbox]
→ [GCN Zero-PIMA phân loại drugname/other] → [Trả JSON danh sách thuốc]
→ [App hiển thị bảng kế hoạch uống theo tuần]
→ [User chọn: 1-7+ ngày, chọn buổi sáng/trưa/chiều/tối/tùy chỉnh]
→ [App gợi ý giờ mặc định + user tùy chỉnh]
→ [User xác nhận/chỉnh sửa] → [Lưu lịch vào SQLite] → [Đặt local notification]
```

> [!NOTE]
> **Multi-prescriptions:** Mỗi lần chỉ xử lý 1 đơn thuốc. Nếu user có nhiều đơn
> khác nhau → scan từng đơn riêng lẻ. App lưu từng đơn vào SQLite độc lập.


**Luồng B — Quét thuốc & Uống:**
```
[Nhận thông báo nhắc uống thuốc] → [Mở App]
→ [Chụp ảnh tất cả viên thuốc cần uống buổi đó]
→ [Gửi ảnh → FastAPI] → [Faster R-CNN detect từng viên]
→ [Zero-PIMA matching: ảnh viên thuốc ↔ tên thuốc trong đơn]
→ [Trả kết quả: viên nào đúng, viên nào sai/thiếu]
→ [App hiển thị kết quả so sánh] → [User xác nhận đã uống]
```

---

## 2. Chi Tiết Chức Năng

### 2.1 Chức năng bắt buộc (MVP)

| # | Chức năng | Mô tả | Đầu vào | Đầu ra |
|---|---|---|---|---|
| F1 | Scan toa thuốc | Chụp ảnh đơn thuốc từ camera | Ảnh đơn thuốc | JSON danh sách thuốc |
| F2 | OCR + GCN trích xuất | PaddleOCR đọc text, GCN phân loại drugname | Ảnh đã crop | Tên thuốc + liều + cách uống |
| F3 | Lập lịch uống thuốc | Hiển thị bảng tuần, chọn buổi/ngày | Danh sách thuốc | Lịch uống cá nhân |
| F4 | Nhắc uống thuốc | Local notification đúng giờ | Lịch đã lưu | Push notification |
| F5 | Quét viên thuốc | Chụp ảnh viên thuốc, AI so sánh với đơn | Ảnh viên thuốc | Kết quả matching đúng/sai |
| F6 | Xác nhận đã uống | Ghi lại lịch sử uống thuốc | User tap | Log uống thuốc |
| F7 | Lịch sử toa thuốc | Xem lại các toa đã scan | - | Danh sách toa thuốc |
| F8 | Tra cứu thuốc | Tìm thông tin thuốc từ nguồn công khai | Tên thuốc | Mô tả, công dụng, tác dụng phụ |

### 2.2 Chức năng mở rộng sau (nếu có thời gian)

| # | Chức năng | Ghi chú |
|---|---|---|
| E1 | Giải thích thuốc bằng LLM | Gemini API giải thích thuốc đơn giản |
| E2 | Cảnh báo tương tác thuốc | Kiểm tra 2 thuốc có xung đột |
| E3 | Theo dõi số viên còn lại | Trừ dần khi xác nhận uống |
| E4 | Family Mode | Quản lý thuốc cho nhiều người |
| E5 | Cloud sync | Đồng bộ lên server, đăng nhập tài khoản |

---

## 3. Dữ Liệu

### 3.1 Dataset viên thuốc

**Nguồn chính:**
- **Kaggle "Pills Detection Dataset"** (by Alexander Y.) — bao gồm VAIPE re-annotated, ảnh viên thuốc VN, có labels + bounding boxes
- **Zero-PIMA `config.py`** — 107 loại thuốc VN đã có tên chuẩn
- **Zero-PIMA `pill_information.csv`** — 107 thuốc với color + shape

**Chiến lược dữ liệu:**
1. Download dataset Kaggle (VAIPE pills) → lấy ảnh + tên thuốc VN
2. Dùng danh sách 107 thuốc từ `config.py` (đã có tên + color + shape)
3. Tự tạo ~10-20 mẫu đơn thuốc JSON dùng các thuốc trong danh sách
4. Train/test Zero-PIMA matching trên dữ liệu này

### 3.2 Bổ sung pill_information (color, shape)

**Nguồn crawl thêm:**
- [drugbank.vn](https://drugbank.vn) — thông tin thuốc VN, có hình ảnh, mô tả
- [thuocbietduoc.com.vn](https://thuocbietduoc.com.vn) — database thuốc biệt dược VN
- [drugs.com](https://www.drugs.com/pill_identification.html) — pill identifier quốc tế (color, shape, imprint)

**Dữ liệu cần crawl cho mỗi thuốc:**
```
Pill, Color, Shape, Description, Usage, SideEffects, ImageURL
```

### 3.3 Mẫu đơn thuốc JSON (đầu vào cho Zero-PIMA)

Mỗi đơn thuốc cần chuyển thành format Zero-PIMA:

```json
[
  {
    "text": "BỘ Y TẾ",
    "label": "other",
    "box": [50, 10, 200, 40],
    "mapping": null
  },
  {
    "text": "Paracetamol 500mg",
    "label": "drugname",
    "box": [30, 200, 350, 230],
    "mapping": "Paracetamol-500mg"
  },
  {
    "text": "Ngày uống 2 viên sau ăn",
    "label": "other",
    "box": [360, 200, 600, 230],
    "mapping": null
  }
]
```

> [!IMPORTANT]
> Mỗi text block cần: `text` (nội dung OCR), `label` (drugname/other), `box` (tọa độ bbox), `mapping` (tên chuẩn trong `ALL_PILL_LABELS` nếu là drugname).

### 3.4 Lưu trữ trong App (SQLite)

```sql
-- Toa thuốc
CREATE TABLE prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT,
    hospital_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Thuốc trong toa
CREATE TABLE medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER REFERENCES prescriptions(id),
    drug_name TEXT NOT NULL,
    dosage TEXT,
    unit TEXT,
    quantity INTEGER,
    instructions TEXT,
    pill_label TEXT  -- mapping tới ALL_PILL_LABELS cho Zero-PIMA matching
);

-- Lịch nhắc
CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id INTEGER REFERENCES medications(id),
    day_of_week INTEGER,  -- 0=Mon, 6=Sun
    session TEXT,          -- 'sáng', 'trưa', 'chiều', 'tối', hoặc custom
    time TEXT,             -- '07:00', '12:00', '18:00', '21:00'
    is_active BOOLEAN DEFAULT 1
);

-- Lịch sử uống
CREATE TABLE medication_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER REFERENCES schedules(id),
    scheduled_time DATETIME,
    actual_time DATETIME,
    status TEXT,  -- 'taken', 'skipped', 'missed'
    pill_verified BOOLEAN DEFAULT 0  -- đã quét xác nhận viên thuốc chưa
);
```

---

## 4. Pipeline AI — Chi Tiết Kỹ Thuật

### 4.1 Pipeline tổng quan

```
                    PHẦN ĐÃ CÓ                         CẦN LÀM
                    ──────────                         ────────
Ảnh đơn thuốc ──► YOLO11-seg ──► Crop mask ──► Preprocessing ──► PaddleOCR
     │                                                               │
     │                                              text + bbox (JSON output)
     │                                                               │
     │                                                    ┌──────────▼──────────┐
     │                                                    │  OCR→Zero-PIMA      │
     │                                                    │  Converter           │
     │                                                    │  (CẦN XÂY DỰNG)     │
     │                                                    └──────────┬──────────┘
     │                                                               │
     │                                                    Zero-PIMA JSON format
     │                                                               │
     │                                        ┌──────────────────────▼──────────┐
     │                                        │  GCN (Graph Convolutional Net)  │
     │                                        │  Phân loại: drugname / other    │
     │                                        └──────────────────────┬──────────┘
     │                                                               │
     │                                              Danh sách tên thuốc (drugname)
     │                                                               │
     │                                        ┌──────────────────────▼──────────┐
Ảnh viên thuốc ──► Faster R-CNN ──► Features ─┤  Contrastive Matching          │
                   (detect viên)               │  ảnh viên thuốc ↔ tên thuốc   │
                                                └──────────────────────┬────────┘
                                                                       │
                                                               Matching result
                                                       (viên X = thuốc Y? đúng/sai)
```

### 4.2 Module cần xây dựng mới

#### 4.2.1 OCR → Zero-PIMA Converter

**File:** `core/converter/ocr_to_pima.py`

**Chức năng:** Chuyển output PaddleOCR (text + bbox) sang format JSON của Zero-PIMA.

**Input:** PaddleOCR result (list of `[bbox, (text, confidence)]`)
```python
# PaddleOCR output format
[
    [[[30, 200], [350, 200], [350, 230], [30, 230]], ("Paracetamol 500mg", 0.95)],
    [[[360, 200], [600, 200], [600, 230], [360, 230]], ("Ngày uống 2 viên", 0.88)],
]
```

**Output:** Zero-PIMA JSON format
```python
[
    {"text": "Paracetamol 500mg", "label": "other", "box": [30, 200, 350, 230], "mapping": null},
    {"text": "Ngày uống 2 viên", "label": "other", "box": [360, 200, 600, 230], "mapping": null},
]
```

> [!NOTE]
> Ban đầu tất cả label đặt là `"other"`. GCN sẽ tự predict label `"drugname"` khi inference.
> Field `mapping` ban đầu = null, sau khi GCN predict drugname, cần thêm bước map text sang `ALL_PILL_LABELS`.

#### 4.2.2 Drugname Mapper

**File:** `core/converter/drug_mapper.py`

**Chức năng:** Sau khi GCN predict một text block là "drugname", map text đó sang tên chuẩn trong `ALL_PILL_LABELS`.

**Approach:** Fuzzy string matching (dùng `fuzzywuzzy` hoặc `rapidfuzz`) giữa OCR text và danh sách 107+ thuốc.

```python
# Ví dụ:
ocr_text = "Paracetamol 500mg"
matched = fuzzy_match(ocr_text, ALL_PILL_LABELS.keys())
# → "Paracetamol-500mg" (score: 95)
```

#### 4.2.3 FastAPI Server

**File:** `server/main.py`

**Endpoints:**

| Method | Endpoint | Input | Output | Mô tả |
|---|---|---|---|---|
| POST | `/api/scan-prescription` | Ảnh đơn thuốc (multipart) | JSON danh sách thuốc | Full pipeline: YOLO → OCR → GCN → mapping |
| POST | `/api/scan-pills` | Ảnh viên thuốc + prescription_id | JSON matching result | Zero-PIMA matching |
| GET | `/api/drug-info/{name}` | Tên thuốc | JSON thông tin thuốc | Tra cứu từ local DB |
| GET | `/api/health` | - | Status | Health check |

#### 4.2.4 Drug Information Database

**File:** `server/data/drug_db.json` hoặc SQLite

**Nguồn:** Crawl từ drugbank.vn + thuocbietduoc.com.vn

**Format:**
```json
{
    "Paracetamol-500mg": {
        "generic_name": "Paracetamol",
        "brand_names": ["Panadol", "Hapacol", "Efferalgan"],
        "color": "white",
        "shape": "oblong",
        "usage": "Giảm đau, hạ sốt",
        "dosage_info": "Người lớn: 1-2 viên/lần, 3-4 lần/ngày",
        "side_effects": "Hiếm gặp: dị ứng da, buồn nôn",
        "image_url": "..."
    }
}
```

---

## 5. Phases — Các Giai Đoạn Thực Hiện

### Phase 1: Chuẩn bị Dữ liệu & Môi trường

> [!TIP]
> Phase này là nền tảng — không có dữ liệu tốt thì model không chạy được.

#### 1.1 Download & tổ chức dataset viên thuốc
- [x] Download "Pills Detection Dataset" từ Kaggle
- [x] Phân tích cấu trúc dataset: ảnh, labels, annotations format
- [x] Map các loại thuốc trong dataset với `ALL_PILL_LABELS` (107 thuốc Zero-PIMA)
- [x] Tổ chức ảnh theo cấu trúc thư mục Zero-PIMA yêu cầu:
  ```
  data/
  ├── pills/
  │   ├── train/
  │   │   ├── imgs/       # Ảnh viên thuốc
  │   │   └── labels/     # JSON bbox + labels
  │   └── test/
  │       ├── imgs/
  │       └── labels/
  └── pres/
      ├── train/          # JSON đơn thuốc
      └── test/
  ```
- [x] Nếu dataset Kaggle không đủ, tìm thêm nguồn bổ sung

#### 1.2 Crawl thông tin thuốc (color, shape, mô tả)
- [ ] Viết script crawl từ drugbank.vn hoặc thuocbietduoc.com.vn
- [ ] Thu thập: tên, màu sắc, hình dạng, công dụng, tác dụng phụ
- [ ] Cập nhật/mở rộng `pill_information.csv` (từ 107 → nhiều hơn nếu cần)
- [ ] Lưu vào `server/data/drug_db.json`

#### 1.3 Tạo mẫu đơn thuốc JSON
- [x] Tạo 938 file JSON đơn thuốc format BVĐK
- [x] Mỗi đơn dùng thuốc có trong `ALL_PILL_LABELS`
- [x] Đảm bảo mỗi text block có: text, label, box, mapping
- [x] Chia train: 938 train (BVĐK format)
- [ ] Tạo test set format BVĐK (118 prescriptions)

#### 1.4 Cài đặt môi trường
- [x] Setup venv cho Zero-PIMA (PyTorch, PyG, transformers, timm)
- [ ] Cài Flutter SDK + Android Studio + Android Emulator
- [ ] Cài FastAPI + uvicorn
- [x] Verify GPU hoạt động (CUDA) — Colab T4

---

### Phase 2: Train AI Models (Zero-PIMA)

> [!IMPORTANT]
> Phase này là phần AI cốt lõi. Cần GPU. Train trên Colab Pro.

#### 2.1 Chuẩn bị training
- [x] Verify data format đúng với Zero-PIMA expectations
- [x] Copy `roi_heads.py` thay thế file mặc định Faster RCNN (theo README Zero-PIMA)
- [x] Chỉnh `config.py`: cập nhật `ALL_PILL_LABELS`
- [x] Cập nhật `pill_information.csv` với thuốc mới
- [x] Chỉnh `utils/option.py`: paths, hyperparameters
- [x] Dry run kiểm tra data loading thành công

#### 2.2 Train Faster R-CNN (Pill Localization)
- [x] Train detect viên thuốc trong ảnh (2 classes: background + pill)
- [ ] Đánh giá trên test set: mAP, recall
- [x] Lưu best checkpoint

#### 2.3 Train PrescriptionPill matching model
- [x] Train GCN phân loại drugname/other trên prescription JSON (50 epoch, VAIPE format)
- [/] Fine-tune trên BVĐK format (epoch 51→100, đang chạy trên Colab)
- [ ] Evaluate: matching accuracy trên test set
- [ ] Evaluate unseen pills (zero-shot capability)
- [x] Lưu best checkpoints cho cả localization + matching models

#### 2.4 Test inference pipeline
- [ ] Viết script inference end-to-end:
  - Input: 1 ảnh viên thuốc + 1 prescription JSON
  - Output: matching result
- [ ] Test với nhiều trường hợp:
  - Thuốc đúng với đơn
  - Thuốc sai với đơn
  - Thuốc thiếu
  - Thuốc chưa từng thấy (zero-shot)

---

### Phase 3: Xây dựng OCR → Zero-PIMA Converter

> [!NOTE]
> Đây là cầu nối giữa OCR pipeline (đã có) và Zero-PIMA (Phase 2).

#### 3.1 OCR → Zero-PIMA JSON converter
- [x] Tạo `core/converter/__init__.py`
- [x] Tạo `core/converter/ocr_to_pima.py`
  - Input: PaddleOCR result (list of bbox + text + confidence)
  - Output: Zero-PIMA format JSON (text, label="other", box, mapping=null)
  - Normalize bbox format: PaddleOCR 4-point → Zero-PIMA [xmin, ymin, xmax, ymax]
- [x] Test với output OCR thật từ `output/step-3_ocr-paddle/json/`

#### 3.2 Drugname Mapper
- [x] Tạo `core/converter/drug_mapper.py`
  - Fuzzy matching: OCR text → `ALL_PILL_LABELS` keys
  - Threshold: chỉ accept match score > 70%
  - Fallback: nếu không match → giữ text gốc, đánh dấu "unmatched"
- [x] Test accuracy: đưa 10+ tên thuốc OCR → kiểm tra map đúng

#### 3.3 Full prescription processing pipeline
- [ ] Tạo `core/pipeline.py` — orchestrate toàn bộ:
  ```python
  def process_prescription(image) -> dict:
      # 1. YOLO detect & crop
      # 2. Preprocessing (rotate, orientation)
      # 3. PaddleOCR (text + bbox)
      # 4. Convert to Zero-PIMA format
      # 5. GCN predict drugname/other
      # 6. Map drugname to ALL_PILL_LABELS
      # 7. Return structured result
  ```
- [ ] Test end-to-end với ảnh đơn thuốc thật

---

### Phase 4: FastAPI Backend Server

#### 4.1 Cấu trúc server
- [ ] Tạo thư mục `server/`
  ```
  server/
  ├── main.py              # FastAPI app
  ├── routers/
  │   ├── prescription.py  # /api/scan-prescription
  │   ├── pill_match.py    # /api/scan-pills
  │   └── drug_info.py     # /api/drug-info
  ├── models/              # Pydantic schemas
  │   ├── prescription.py
  │   ├── medication.py
  │   └── matching.py
  ├── services/            # Business logic
  │   ├── ocr_service.py
  │   ├── matching_service.py
  │   └── drug_service.py
  ├── data/
  │   └── drug_db.json     # Drug information database
  └── config.py            # Server config (model paths, ports)
  ```

#### 4.2 Implement endpoints
- [ ] `POST /api/scan-prescription`
  - Nhận ảnh multipart → chạy full pipeline (Phase 3) → trả JSON
  - Response format:
    ```json
    {
      "medications": [
        {
          "drug_name": "Paracetamol-500mg",
          "ocr_text": "Paracetamol 500mg",
          "confidence": 0.95,
          "dosage": "2 viên/ngày",
          "instructions": "Sau ăn",
          "suggested_sessions": ["sáng", "tối"],
          "suggested_time": ["07:00", "21:00"]
        }
      ]
    }
    ```
- [ ] `POST /api/scan-pills`
  - Nhận ảnh viên thuốc + danh sách tên thuốc expected
  - Chạy Faster R-CNN + Zero-PIMA matching
  - Response: danh sách viên thuốc detect được + matching result
- [ ] `GET /api/drug-info/{name}`
  - Tra cứu từ `drug_db.json`
  - Response: thông tin thuốc (công dụng, tác dụng phụ, color, shape)

#### 4.3 Test server
- [ ] Test từng endpoint bằng Postman/cURL
- [ ] Test với ảnh đơn thuốc thật
- [ ] Test với ảnh viên thuốc
- [ ] Đảm bảo response time chấp nhận được

---

### Phase 5: Flutter App (Android)

#### 5.1 Setup & Cấu trúc
- [ ] Tạo Flutter project: `flutter create medicine_app`
- [ ] Setup dependencies (pubspec.yaml):
  - `camera` — chụp ảnh
  - `http` / `dio` — gọi API
  - `sqflite` — SQLite local
  - `flutter_local_notifications` — nhắc uống thuốc
  - `provider` hoặc `riverpod` — state management
- [ ] Cấu trúc folder:
  ```
  lib/
  ├── main.dart
  ├── models/           # Data models
  ├── screens/          # Các màn hình
  ├── services/         # API calls, DB, notifications
  ├── widgets/          # UI components tái sử dụng
  └── utils/            # Helpers
  ```

#### 5.2 Các màn hình cần xây dựng

**Screen 1: Home — Dashboard**
- Hiển thị thuốc cần uống hôm nay
- Nút "Quét đơn thuốc mới"
- Nút "Quét viên thuốc"
- Lịch sử toa thuốc

**Screen 2: Camera Scan — Quét đơn thuốc**
- Camera preview toàn màn hình
- Nút chụp ảnh
- Loading indicator khi gửi API
- Hiển thị kết quả OCR để user xác nhận

**Screen 3: Schedule Setup — Lập lịch uống thuốc**
- Danh sách thuốc từ OCR
- Cho mỗi thuốc:
  - Chọn ngày trong tuần (checkboxes: T2-CN, hoặc custom)
  - Chọn buổi: sáng/trưa/chiều/tối (multi-select)
  - App gợi ý giờ mặc định, user có thể chỉnh
  - Nhập số lượng viên mỗi lần
- Nút "Xác nhận & Lưu"

**Screen 4: Pill Scanner — Quét viên thuốc**
- Camera chụp ảnh các viên thuốc
- Gửi API → nhận matching result
- Hiển thị: viên nào đúng (✅), sai (❌), thiếu (⚠️)
- Nút "Xác nhận đã uống"

**Screen 5: History — Lịch sử**
- Danh sách toa thuốc đã scan
- Xem lại chi tiết từng toa
- Lịch sử uống thuốc theo ngày

**Screen 6: Drug Info — Tra cứu thuốc**
- Tìm kiếm theo tên
- Hiển thị: công dụng, cách dùng, tác dụng phụ, hình ảnh

#### 5.3 Services
- [ ] `api_service.dart` — gọi FastAPI endpoints
- [ ] `database_service.dart` — CRUD SQLite (prescriptions, medications, schedules, logs)
- [ ] `notification_service.dart` — schedule/cancel local notifications
- [ ] `camera_service.dart` — camera capture + image processing

#### 5.4 Implement & Test
- [ ] Implement từng screen theo thứ tự: Home → Camera → Schedule → Pill Scanner → History → Drug Info
- [ ] Test trên emulator Android
- [ ] Test gọi API tới FastAPI server qua WiFi
- [ ] Test notifications đúng giờ
- [ ] Test full flow E2E: scan → schedule → nhắc → quét → confirm

---

### Phase 6: Tích Hợp & Demo

#### 6.1 End-to-End Testing
- [ ] Test full Luồng A: Scan đơn → OCR → GCN → Lập lịch → Nhắc nhở
- [ ] Test full Luồng B: Nhận nhắc → Quét thuốc → Matching → Confirm
- [ ] Test edge cases:
  - Đơn thuốc mờ/nghiêng
  - Viên thuốc chồng nhau
  - Thuốc không có trong database

#### 6.2 Demo Setup
- [ ] PC: chạy `uvicorn server.main:app --host 0.0.0.0 --port 8000`
- [ ] Phone: cài app Flutter, kết nối cùng WiFi
- [ ] Chuẩn bị mẫu đơn thuốc + viên thuốc thật để demo
- [ ] Quay video demo (nếu cần)

---

## 6. Cấu Trúc Thư Mục Dự Án (Mới)

```
medicineApp/
├── core/                              # AI modules (giữ code cũ + thêm mới)
│   ├── config.py                      # Config chung
│   ├── detector.py                    # YOLO detection
│   ├── segmentation.py                # Mask/bbox crop
│   ├── visualizer.py                  # Debug visualization
│   ├── preprocessor/                  # Xoay, chỉnh hướng ảnh
│   │   ├── geometric.py
│   │   └── orientation.py
│   ├── ocr/                           # OCR modules
│   │   ├── base.py
│   │   ├── paddle_ocr.py
│   │   └── hybrid_ocr.py
│   ├── converter/                     # [NEW] OCR → Zero-PIMA format
│   │   ├── __init__.py
│   │   ├── ocr_to_pima.py            # Chuyển OCR output → JSON
│   │   └── drug_mapper.py            # Fuzzy match tên thuốc → ALL_PILL_LABELS
│   └── pipeline.py                    # [NEW] Full orchestration pipeline
│
├── Zero-PIMA/                         # Model Zero-PIMA (fork/tham khảo)
│   ├── config.py                      # ALL_PILL_LABELS, UNSEEN_LABELS
│   ├── models/                        # Neural network definitions
│   ├── data/                          # Data loader + pill_information.csv
│   ├── train.py                       # Training script
│   ├── test.py                        # Testing script
│   └── inference.py                   # [NEW] Script inference đơn lẻ
│
├── server/                            # [NEW] FastAPI backend
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── models/
│   └── data/drug_db.json
│
├── medicine_app/                      # [NEW] Flutter Android app
│   ├── lib/
│   ├── android/
│   ├── pubspec.yaml
│   └── ...
│
├── scripts/                           # Utility scripts
│   ├── run_camera.py
│   ├── run_folder.py
│   ├── crawl_drug_info.py             # [NEW] Crawl thông tin thuốc
│   └── create_prescription_json.py    # [NEW] Tạo mẫu đơn thuốc
│
├── data/                              # Data cho training
│   ├── input/                         # Ảnh đơn thuốc
│   ├── pills/                         # [NEW] Dataset viên thuốc (Kaggle)
│   │   ├── train/
│   │   └── test/
│   └── pres/                          # [NEW] JSON đơn thuốc cho Zero-PIMA
│       ├── train/
│       └── test/
│
├── models/weights/                    # Trained model weights
│   ├── best.pt                        # YOLO model
│   ├── localization_best.pth          # [NEW] Faster R-CNN
│   └── matching_best.pth             # [NEW] Zero-PIMA matching
│
├── plan/
│   └── master_plan.md                 # File này
│
└── output/                            # Output trung gian (debug)
```

---

## 7. Công Nghệ & Dependencies

### 7.1 Python Backend (PC)

| Package | Vai trò | Version |
|---|---|---|
| `torch` + `torchvision` | Deep learning framework | ≥2.0 |
| `torch-geometric` | GCN (Graph Neural Network) | ≥2.0 |
| `transformers` | SBERT text encoder | ≥4.30 |
| `timm` | Image encoder backbone | ≥0.9 |
| `ultralytics` | YOLO11 detection | ≥8.0 |
| `paddlepaddle` + `paddleocr` | OCR tiếng Việt | v4 |
| `fastapi` + `uvicorn` | REST API server | ≥0.100 |
| `python-multipart` | File upload handling | - |
| `rapidfuzz` | Fuzzy string matching | ≥3.0 |
| `networkx` | Graph construction | ≥3.0 |
| `wandb` | Training logging (optional) | - |
| `beautifulsoup4` + `requests` | Web crawling | - |

### 7.2 Flutter App (Android)

| Package | Vai trò |
|---|---|
| `camera` | Camera access |
| `dio` | HTTP client (gọi API) |
| `sqflite` | SQLite local database |
| `flutter_local_notifications` | Push notification local |
| `provider` | State management |
| `intl` | Date/time formatting |
| `image_picker` | Chọn ảnh từ gallery |

---

## 8. Rủi Ro & Giải Pháp

| Rủi ro | Khả năng | Giải pháp |
|---|---|---|
| Dataset Kaggle không đủ thuốc VN | Trung bình | Bổ sung từ CISTILY hoặc tự chụp |
| GCN train không tốt với ít data | Cao | Augment data, giảm model size, dùng pretrained |
| OCR đọc sai tên thuốc | Cao | Fuzzy matching + user confirm trước khi lưu |
| Zero-PIMA matching accuracy thấp | Trung bình | Tăng training data, tune hyperparameters |
| Flutter learning curve (chưa biết) | Cao | Dùng template UI, tập trung chức năng core, tham khảo tutorial |
| GPU không đủ mạnh | Thấp | Giảm batch size, dùng MobileNet backbone (đã có trong code) |
| Phone → PC API chậm | Thấp | Nén ảnh trước khi gửi, optimize model inference |

---

## 9. Tiêu Chí Hoàn Thành Demo

- [ ] Chụp đơn thuốc → nhận được danh sách thuốc chính xác
- [ ] Lập lịch uống thuốc theo tuần với chọn buổi
- [ ] Nhận notification nhắc uống thuốc đúng giờ
- [ ] Chụp viên thuốc → matching đúng tên thuốc trong đơn
- [ ] Xác nhận đã uống + lưu lịch sử
- [ ] Tra cứu thông tin thuốc cơ bản

---

## 10. Về Mở Rộng Sau Này

> [!NOTE]
> Kiến trúc hiện tại (Flutter + FastAPI + SQLite) **dễ mở rộng lên production**:

| Hiện tại (Demo) | Mở rộng (Production) | Độ khó |
|---|---|---|
| SQLite local | PostgreSQL + Supabase cloud | ⭐⭐ Dễ |
| FastAPI trên PC | Deploy Docker lên VPS / Cloud Run | ⭐⭐ Dễ |
| Không đăng nhập | Firebase Auth + user accounts | ⭐⭐⭐ Trung bình |
| Local notification | Firebase Cloud Messaging | ⭐⭐ Dễ |
| 1 user | Multi-user + Family Mode | ⭐⭐⭐ Trung bình |
| 107 thuốc | Mở rộng database thuốc VN | ⭐⭐ Dễ (crawl thêm) |

Kiến trúc **Flutter + FastAPI REST API** cho phép chuyển backend lên cloud mà **không cần sửa code app** — chỉ đổi URL API endpoint.

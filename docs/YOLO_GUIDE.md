# Hướng Dẫn YOLO Cho Người Mới Bắt Đầu

## 📌 Mục Lục
1. [YOLO là gì?](#1-yolo-là-gì)
2. [Phiên bản YOLO trong dự án](#2-phiên-bản-yolo-trong-dự-án)
3. [Cấu trúc dự án](#3-cấu-trúc-dự-án)
4. [Luồng xử lý dữ liệu](#4-luồng-xử-lý-dữ-liệu)
5. [Các file code quan trọng](#5-các-file-code-quan-trọng)
6. [Hướng dẫn sử dụng](#6-hướng-dẫn-sử-dụng)
7. [Giải thích từng bước](#7-giải-thích-từng-bước)

---

## 1. YOLO là gì?

**YOLO = You Only Look Once**

YOLO là một mô hình AI để nhận diện và phân đoạn (segmentation) vật thể trong ảnh.

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Ảnh đầu vào   │ ──▶  │   Mô hình YOLO  │ ──▶  │   Kết quả       │
│   (input.jpg)   │      │   (best.pt)     │      │   - Bounding box│
│                 │      │                 │      │   - Mask        │
│                 │      │                 │      │   - Label       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

### Các loại task của YOLO:
| Task | Mô tả | File model |
|------|-------|------------|
| **Detection** | Phát hiện vật thể + bounding box | `yolov8n.pt` |
| **Segmentation** | Phát hiện + tô màu vùng vật thể | `yolov8n-seg.pt` ← **Dự án dùng cái này** |
| **Classification** | Phân loại ảnh | `yolov8n-cls.pt` |
| **Pose** | Nhận diện tư thế người | `yolov8n-pose.pt` |

---

## 2. Phiên bản YOLO Trong Dự Án

### Dự án sử dụng: **YOLOv8n-seg** (Nano Segmentation)

```
YOLOv8n-seg
   │
   ├── v8 = Version 8 (phiên bản mới nhất, nhanh nhất)
   ├── n  = Nano (kích thước nhỏ nhất, nhanh nhất)
   └── seg = Segmentation (phân đoạn vật thể)
```

### So sánh các kích thước model:

| Model | Kích thước | Tốc độ | Độ chính xác | Khi nào dùng? |
|-------|------------|--------|--------------|---------------|
| **Nano (n)** | 6.7 MB | ⚡⚡⚡⚡⚡ | ⭐⭐ | Mobile, real-time |
| Small (s) | 23 MB | ⚡⚡⚡⚡ | ⭐⭐⭐ | Cân bằng |
| Medium (m) | 52 MB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Server |
| Large (l) | 87 MB | ⚡⚡ | ⭐⭐⭐⭐⭐ | High accuracy |
| XLarge (x) | 130 MB | ⚡ | ⭐⭐⭐⭐⭐ | Best accuracy |

**Tại sao chọn Nano?**
- Phù hợp với mobile app (nhẹ, nhanh)
- Đủ tốt cho việc nhận diện thuốc/đơn thuốc
- Có thể nâng cấp lên version lớn hơn sau

---

## 3. Cấu Trúc Dự Án

```
medicineApp/
│
├── 📁 models/                      # 🧠 MODULE MÔ HÌNH
│   ├── __init__.py                 # Export class
│   ├── weights/                    # Chứa file model (.pt)
│   │   └── best.pt                 # ← Model bạn đã train (đặt vào đây)
│   └── yolo_segmentation.py        # ⭐ WRAPPER CLASS CHÍNH
│
├── 📁 inference/                   # 🔮 MODULE INFERENCE
│   ├── __init__.py
│   └── predict.py                  # Script chạy prediction
│
├── 📁 data/                        # 📊 DỮ LIỆU
│   ├── input/                      # ← Đặt ảnh cần xử lý vào đây
│   │   └── *.jpg                   # Ảnh đơn thuốc, thuốc, etc.
│   └── output/                     # ← Kết quả sẽ xuất ra đây
│       └── predict/                # Ảnh đã được đánh dấu
│
├── 📁 scripts/                     # 🚀 SCRIPTS CHẠY NHANH
│   └── run_inference.py            # Entry point để chạy
│
├── config.yaml                     # ⚙️ Cấu hình app
├── requirements.txt                # 📦 Dependencies
└── README.md                       # 📖 Hướng dẫn
```

---

## 4. Luồng Xử Lý Dữ Liệu

### Sơ đồ luồng xử lý:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        LUỒNG XỬ LÝ YOLO                              │
└──────────────────────────────────────────────────────────────────────┘

     INPUT                    PROCESSING                    OUTPUT
┌─────────────┐          ┌─────────────────┐          ┌─────────────┐
│             │          │                 │          │             │
│  data/      │          │  models/        │          │  data/      │
│  input/     │ ──────▶  │  yolo_         │ ──────▶  │  output/    │
│             │          │  segmentation  │          │             │
│  - ảnh.jpg  │          │  .py           │          │  - masks    │
│  - ảnh.png  │          │                 │          │  - boxes    │
│             │          │  + weights/     │          │  - labels   │
│             │          │    best.pt     │          │             │
└─────────────┘          └─────────────────┘          └─────────────┘
       │                         │                          │
       │                         │                          │
       ▼                         ▼                          ▼
   Ảnh gốc              YOLOv8n-seg model            Kết quả phân tích
   (đơn thuốc,          (6.7 MB, fast)               - Vị trí vật thể
   viên thuốc,                                       - Mask phân đoạn
   etc.)                                             - Tên class + %
```

### Chi tiết từng bước:

| Bước | Mô tả | File liên quan |
|------|-------|----------------|
| 1️⃣ | Đặt ảnh vào `data/input/` | - |
| 2️⃣ | Chạy script inference | `scripts/run_inference.py` |
| 3️⃣ | Script gọi wrapper class | `models/yolo_segmentation.py` |
| 4️⃣ | Wrapper load model `.pt` | `models/weights/best.pt` |
| 5️⃣ | Model xử lý ảnh | (ultralytics library) |
| 6️⃣ | Trả về results (boxes, masks) | Python objects |
| 7️⃣ | Lưu kết quả visualization | `data/output/predict/` |

---

## 5. Các File Code Quan Trọng

### 5.1. `models/yolo_segmentation.py` - ⭐ FILE CHÍNH

```python
# Đây là wrapper class bọc YOLO để dễ sử dụng

from ultralytics import YOLO

class YOLOSegmentation:
    """
    Wrapper class cho YOLO Segmentation
    
    Tại sao cần wrapper?
    - Đơn giản hóa việc sử dụng
    - Thêm các method tiện ích
    - Dễ bảo trì và mở rộng
    """
    
    def __init__(self, model_path=None, model_size="nano"):
        # Nếu có custom model → dùng nó
        # Nếu không → dùng pretrained
        if model_path:
            self.model = YOLO(model_path)  # Load: models/weights/best.pt
        else:
            self.model = YOLO("yolov8n-seg.pt")  # Download pretrained
    
    def predict(self, source, conf=0.25):
        # source: đường dẫn ảnh hoặc folder
        # conf: ngưỡng confidence (0.25 = 25%)
        return self.model.predict(source, conf=conf)
    
    def get_masks(self, results):
        # Trích xuất segmentation masks từ kết quả
        # Mask = mảng 2D đánh dấu vùng vật thể
        ...
    
    def get_boxes(self, results):
        # Trích xuất bounding boxes
        # Box = [x1, y1, x2, y2, confidence, class_id]
        ...
```

### 5.2. `inference/predict.py` - Script Chạy Inference

```python
# Script này xử lý command line arguments và gọi model

def run_inference(source, model_path=None, output_dir="data/output"):
    # 1. Khởi tạo model
    model = YOLOSegmentation(model_path=model_path)
    
    # 2. Chạy prediction
    results = model.predict(source=source, save=True, save_dir=output_dir)
    
    # 3. In kết quả
    for result in results:
        print(f"Detected: {len(result.boxes)} objects")
```

### 5.3. `scripts/run_inference.py` - Entry Point

```python
# File này để chạy từ command line
# Gọi: python scripts/run_inference.py --image data/input/test.jpg

from inference.predict import main
main()
```

---

## 6. Hướng Dẫn Sử Dụng

### Bước 1: Kích hoạt môi trường

```bash
cd /home/hongphuoc/Desktop/medicineApp
source venv/bin/activate
```

### Bước 2: Đặt ảnh vào thư mục input

```bash
# Copy ảnh vào data/input/
cp /path/to/your/image.jpg data/input/
```

### Bước 3: Chạy inference

```bash
# Cách 1: Xử lý 1 ảnh
python scripts/run_inference.py --image data/input/image.jpg

# Cách 2: Xử lý cả thư mục
python scripts/run_inference.py --folder data/input/

# Cách 3: Dùng custom model (model bạn đã train)
python scripts/run_inference.py --folder data/input/ --model models/weights/best.pt

# Cách 4: Hiển thị kết quả ngay
python scripts/run_inference.py --image data/input/image.jpg --show
```

### Bước 4: Xem kết quả

```bash
# Kết quả được lưu tại:
ls data/output/predict/

# Mở ảnh kết quả
xdg-open data/output/predict/image.jpg
```

---

## 7. Giải Thích Từng Bước

### 7.1. Khi bạn chạy lệnh:

```bash
python scripts/run_inference.py --image data/input/test.jpg
```

### 7.2. Điều gì xảy ra bên trong:

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: scripts/run_inference.py                                    │
├─────────────────────────────────────────────────────────────────────┤
│ - Nhận argument: --image data/input/test.jpg                        │
│ - Gọi: inference/predict.py                                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: inference/predict.py                                        │
├─────────────────────────────────────────────────────────────────────┤
│ - Import: from models import YOLOSegmentation                       │
│ - Khởi tạo: model = YOLOSegmentation(model_size="nano")             │
│ - Đây là lúc model yolov8n-seg.pt được load vào RAM                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: models/yolo_segmentation.py                                 │
├─────────────────────────────────────────────────────────────────────┤
│ - Load model: self.model = YOLO("yolov8n-seg.pt")                   │
│ - Model được download lần đầu (6.7 MB)                              │
│ - Sau đó cache lại, không cần download nữa                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: model.predict()                                             │
├─────────────────────────────────────────────────────────────────────┤
│ - Đọc ảnh: data/input/test.jpg                                      │
│ - Resize ảnh về 640x640 (chuẩn YOLO)                                │
│ - Chạy qua neural network                                           │
│ - Trả về: Results object                                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Results object chứa gì?                                     │
├─────────────────────────────────────────────────────────────────────┤
│ results[0].boxes:                                                   │
│   - Bounding boxes: [[x1, y1, x2, y2], ...]                         │
│   - Confidence: [0.95, 0.87, ...]                                   │
│   - Class IDs: [0, 1, 2, ...]                                       │
│                                                                     │
│ results[0].masks:                                                   │
│   - Segmentation masks (mảng 2D True/False)                         │
│   - Đánh dấu vùng thuộc vật thể                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: Lưu kết quả                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ - Vẽ bounding box lên ảnh gốc                                       │
│ - Tô màu vùng segmentation                                          │
│ - Ghi label + confidence %                                          │
│ - Lưu vào: data/output/predict/test.jpg                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3. Output trả về:

```python
# Trong code Python, bạn có thể lấy:

results = model.predict("image.jpg")

for result in results:
    # Bounding boxes
    boxes = result.boxes.xyxy      # Tọa độ [x1, y1, x2, y2]
    confs = result.boxes.conf      # Confidence scores
    classes = result.boxes.cls     # Class IDs
    
    # Segmentation masks
    masks = result.masks.data      # Mảng 2D (H x W)
    
    # Class names
    names = result.names           # {0: "person", 1: "car", ...}
```

---

## 📝 Tóm Tắt

| Câu hỏi | Trả lời |
|---------|---------|
| **Dùng YOLO nào?** | YOLOv8n-seg (Nano Segmentation) |
| **Tại sao?** | Nhẹ (6.7MB), nhanh, phù hợp mobile |
| **Input ở đâu?** | `data/input/` |
| **Output ở đâu?** | `data/output/predict/` |
| **File chính?** | `models/yolo_segmentation.py` |
| **Cách chạy?** | `python scripts/run_inference.py --image <path>` |

---

*Tài liệu tạo: 24/01/2026*
*Dự án: Medicine App - Ứng dụng nhắc nhở uống thuốc*

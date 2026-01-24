# Medicine App

Ứng dụng nhắc nhở uống thuốc với tích hợp YOLO Segmentation.

## Cấu trúc dự án

```
medicineApp/
├── venv/                       # Virtual environment
├── models/                     # Module models
│   ├── weights/                # Chứa file .pt model
│   └── yolo_segmentation.py    # Wrapper class YOLO
├── inference/                  # Module inference
│   └── predict.py              # Script prediction
├── data/
│   ├── input/                  # Ảnh đầu vào
│   └── output/                 # Kết quả segmentation
├── scripts/
│   └── run_inference.py        # Quick run script
├── requirements.txt
└── README.md
```

## Thiết lập môi trường

### 1. Kích hoạt Virtual Environment

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

## Sử dụng YOLO Segmentation

### Model mặc định (YOLOv8n-seg)

Sử dụng pretrained model YOLOv8n-seg (nano - nhanh nhất):

```python
from models import YOLOSegmentation

# Khởi tạo với pretrained model
model = YOLOSegmentation(model_size="nano")

# Chạy inference
results = model.predict("path/to/image.jpg")

# Lấy masks
masks = model.get_masks(results)
```

### Custom trained model

Sử dụng model đã train:

```python
model = YOLOSegmentation(model_path="models/weights/best.pt")
results = model.predict("path/to/image.jpg", conf=0.25)
```

### Các phiên bản model có sẵn

| Model | File | Tốc độ | Độ chính xác |
|-------|------|--------|--------------|
| Nano | `yolov8n-seg.pt` | ⚡⚡⚡⚡⚡ | ⭐⭐ |
| Small | `yolov8s-seg.pt` | ⚡⚡⚡⚡ | ⭐⭐⭐ |
| Medium | `yolov8m-seg.pt` | ⚡⚡⚡ | ⭐⭐⭐⭐ |
| Large | `yolov8l-seg.pt` | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| XLarge | `yolov8x-seg.pt` | ⚡ | ⭐⭐⭐⭐⭐ |

## Chạy Inference từ Command Line

```bash
# Với pretrained model
python scripts/run_inference.py --image data/input/test.jpg

# Với custom model
python scripts/run_inference.py --image data/input/test.jpg --model models/weights/best.pt

# Xử lý cả thư mục
python scripts/run_inference.py --folder data/input/ --output data/output/

# Xem kết quả trên màn hình
python scripts/run_inference.py --image test.jpg --show
```

### Các tham số

| Tham số | Mô tả | Mặc định |
|---------|-------|----------|
| `--image`, `-i` | Đường dẫn ảnh | - |
| `--folder`, `-f` | Đường dẫn thư mục ảnh | - |
| `--model`, `-m` | Custom model .pt | Pretrained |
| `--output`, `-o` | Thư mục output | `data/output` |
| `--conf` | Ngưỡng confidence | 0.25 |
| `--show` | Hiển thị kết quả | False |

---
*Ngày tạo: 24/01/2026*

# Medicine App

Ứng dụng nhắc nhở uống thuốc với tích hợp YOLO Segmentation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Cấu trúc dự án

```
medicineApp/
├── 📁 models/                  # Module YOLO models
│   ├── weights/                # Chứa file .pt model
│   └── yolo_segmentation.py    # Wrapper class
├── 📁 inference/               # Module inference
│   └── predict.py              # Script prediction
├── 📁 data/
│   ├── input/                  # Ảnh đầu vào
│   └── output/                 # Kết quả (ignored)
├── 📁 scripts/
│   └── run_inference.py        # Quick run script
├── 📁 tests/                   # Unit tests
│   ├── test_yolo_model.py
│   └── test_inference.py
├── 📁 docs/                    # Documentation
│   └── PROJECT_RULES.md
├── .gitignore
├── LICENSE                     # MIT License
├── README.md
├── requirements.txt
└── pyproject.toml              # Package config
```

## Thiết lập môi trường

### 1. Clone repository

```bash
git clone https://github.com/hongphuoc6104/medicineApp.git
cd medicineApp
```

### 2. Tạo và kích hoạt Virtual Environment

```bash
# Tạo venv
python3 -m venv venv

# Kích hoạt (Linux/macOS)
source venv/bin/activate

# Kích hoạt (Windows)
venv\Scripts\activate
```

### 3. Cài đặt Dependencies

```bash
pip install -r requirements.txt

# Hoặc cài với dev dependencies
pip install -e ".[dev]"
```

## Sử dụng YOLO Segmentation

### Model mặc định (YOLOv8n-seg)

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

## Chạy Tests

```bash
# Chạy tất cả tests
pytest

# Chạy với coverage
pytest --cov=models --cov=inference
```

## License

MIT License - xem file [LICENSE](LICENSE)

---
*Ngày tạo: 24/01/2026*

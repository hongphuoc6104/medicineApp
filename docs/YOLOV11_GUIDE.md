# Hướng dẫn Run Custom YOLOv11 Segmentation

Hướng dẫn này giúp bạn sử dụng mô hình YOLOv11n-seg đã train (`best.pt`) để chạy inference.

## 1. Chuẩn bị Môi trường

Do lỗi `externally-managed-environment` của Python trên Linux, bạn cần tạo Virtual Environment (venv):

```bash
# 1. Tạo venv
python3 -m venv venv

# 2. Kích hoạt venv
source venv/bin/activate

# 3. Cài đặt thư viện
pip install -r requirements.txt
```

> **Lưu ý:** Tất cả các lệnh sau cần chạy khi **đã kích hoạt venv**.

## 2. Thêm Model vào Project

Copy file `best.pt` bạn đã train vào thư mục `models/weights/`:

```bash
cp /đường/dẫn/tới/best.pt models/weights/best.pt
```

## 3. Cách Code & Sử dụng

### Cách 1: Sử dụng Script có sẵn (Khuyên dùng)

Mình đã tạo sẵn script `scripts/demo_yolov11.py` để bạn test nhanh.

Sửa đường dẫn model trong `scripts/demo_yolov11.py` (nếu cần) hoặc chỉ cần chạy:

```bash
# Chạy với ảnh mẫu (tự động tải nếu không có)
python scripts/demo_yolov11.py

# Hoặc dùng script inference đầy đủ tính năng:
python scripts/run_inference.py --model models/weights/best.pt --image data/input/test.jpg --conf 0.5
```

### Cách 2: Tự viết Code Python

Nếu bạn muốn tích hợp vào code riêng, đây là đoạn code mẫu:

```python
from ultralytics import YOLO

# 1. Load model
model = YOLO("models/weights/best.pt")

# 2. Run inference
# source: đường dẫn ảnh, video, hoặc camera ID (0)
results = model.predict(source="data/input/test.jpg", save=True, conf=0.5)

# 3. Xử lý kết quả
for result in results:
    # Lấy masks (segmentation)
    if result.masks:
        masks = result.masks.data.cpu().numpy()
        print(f"Detected {len(masks)} objects with masks")
    
    # Lấy boxes
    boxes = result.boxes
    for box in boxes:
        print(f"Class: {result.names[int(box.cls)]}, Conf: {float(box.conf):.2f}")
```

## 4. Giải thích các tham số quan trọng

- `conf`: Ngưỡng tin cậy (0.0 - 1.0). Ví dụ `conf=0.25` nghĩa là chỉ lấy các object có độ tin cậy >= 25%.
- `iou`: Ngưỡng Intersection over Union để loại bỏ các box chồng nhau (Non-Max Suppression).
- `save`: Lưu ảnh kết quả (vẽ box/mask lên ảnh).
- `device`: Chọn device chạy (`'cpu'`, `'cuda'`, `'mps'` cho Mac, `'0'`, `'1'`...).

## 5. Troubleshooting (Lỗi thường gặp)

- **Lỗi `ModuleNotFoundError: No module named 'ultralytics'`**:
  -> Bạn chưa activate venv hoặc chưa chạy `pip install -r requirements.txt`.

- **Lỗi `FileNotFoundError` với model**:
  -> Kiểm tra lại đường dẫn tới file `.pt`. Nên để trong `models/weights/` cho gọn.

- **Kết quả không chính xác**:
  -> Thử giảm `conf` (ví dụ `conf=0.1`) xem model có bắt được gì không.
  -> Kiểm tra xem ảnh đầu vào có giống với dữ liệu train không (kích thước, ánh sáng...).

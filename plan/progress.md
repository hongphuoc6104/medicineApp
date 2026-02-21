# 📋 Project Context & To-Do List
# Cập nhật mỗi khi hoàn thành 1 bước nhỏ. Khi Task Lớn xong → chuyển sang GUIDCODE/ hoặc xóa.
# Status: [ ] chưa làm | [/] đang làm | [x] xong
# -----------------------------------------------------------------------

## 📁 THƯ MỤC CẦN TẠO (Folders)
- [x] `core/` — Chứa các module xử lý cốt lõi
- [x] `scripts/` — Chứa các file chạy chính (run_webcam, run_folder)
- [x] `data/input/` — Thư mục ảnh đầu vào cho Batch Mode
- [x] `data/output/` — Thư mục kết quả đầu ra
- [x] `plan/` — Thư mục chứa file ngữ cảnh này
- [x] `models/weights/` — Chứa file best.pt (pre-trained YOLOv11n-seg)

---

## 📄 FILE & HÀM CẦN TẠO (Files & Functions)

### 1. `core/config.py` — Cấu hình hằng số
- [x] `MODEL_PATH = "models/weights/best.pt"`
- [x] `CONF_THRESHOLD = 0.8`
- [x] `INPUT_DIR = "data/input"`
- [x] `OUTPUT_DIR = "data/output"`
- [ ] `CAMERA_INDEX = 0` ← chưa thêm

### 2. `core/detector.py` — Load & chạy model YOLO (< 200 dòng)
- [x] `class PrescriptionDetector:`
- [x] `__init__(self, model_path: str) -> None` — Load YOLO model
- [x]`predict(self, frame: np.ndarray) -> list` — Chạy inference, trả về results

### 3. `core/segmentation.py` — Xử lý mask & tọa độ (< 200 dòng)
- [x] `extract_polygon(result) -> list[list[float]]` — Lấy tọa độ polygon [x1,y1,x2,y2...] từ result.masks
- [x] `crop_by_mask(image: np.ndarray, result) -> np.ndarray` — Cắt ảnh theo mask, nền trong suốt (RGBA)
- [x] `crop_by_bbox(image: np.ndarray, bbox: list) -> np.ndarray` — Cắt ảnh theo bounding box hình chữ nhật

### 4. `core/visualizer.py` — Vẽ debug lên ảnh (< 200 dòng)
- [x] `draw_bbox(image: np.ndarray, bbox: list, label: str) -> np.ndarray` — Vẽ bounding box + nhãn
- [x] `draw_mask_overlay(image: np.ndarray, mask: np.ndarray) -> np.ndarray` — Phủ mask màu lên ảnh gốc
- [x] `draw_polygon_points(image: np.ndarray, points: list) -> np.ndarray` — Vẽ các điểm polygon lên ảnh

### 5. `scripts/run_webcam.py` — Chế độ Camera trực tiếp
- [x] Mở webcam (auto-fallback index 0 → 1 → 2)
- [x] Hiển thị live detection (bbox + mask overlay + polygon)
- [x] Nhấn `s`: Lưu 4 subfolders vào `debug/YOLO/` (original, bbox, mask, polygon .txt)
- [x] Nhấn `q`: Thoát
- [x] Cửa sổ hiển thị cố định kích thước `cv2.WINDOW_NORMAL`

### 6. `scripts/run_folder.py` — Chế độ xử lý hàng loạt
- [x] Đọc tất cả `.jpg/.png` trong `data/input/`
- [x] Chạy YOLO trên từng ảnh — xử lý lần lượt (Option A)
- [x] Nếu KHÔNG phát hiện → print warning với tên file, bỏ qua
- [x] Nếu phát hiện → Lưu 4 subfolders vào `data/output/`:
  - [x] `data/output/original/` — ảnh gốc
  - [x] `data/output/bbox/` — cắt bbox (có padding)
  - [x] `data/output/mask/` — cắt mask (nền đen)
  - [x] `data/output/polygon/` — tọa độ `.txt`
- [x] In tổng kết: số ảnh xử lý / số ảnh phát hiện thành công

---

## 🧪 TESTING
- [ ] Unit test `segmentation.py`: test extract_polygon với mock result
- [ ] Manual test webcam: bấm 's', kiểm tra file output
- [ ] Manual test folder: bỏ 3 ảnh vào input, chạy script, kiểm tra output

---

## 📚 GUIDCODE (Viết sau khi xong)
- [ ] User viết `GUIDCODE/01_YOLO_Pipeline.md` bằng tiếng Anh
- [ ] AI review ngữ pháp + kỹ thuật

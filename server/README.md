# Server (FastAPI / AI Bridge)

ĐÂY LÀ AI BRIDGE DÀNH RIÊNG CHO VIỆC CHẠY MODEL (Python). **Đây không phải Backend của ứng dụng sản phẩm chính**. 
API Backend xử lý business logic và mobile request chủ yếu nằm ở thư mục `server-node/` (Node.js). Node.js sẽ đại diện cho client gọi sang FastAPI proxy này mỗi khi cần kích hoạt chức năng AI (như OCR, NER).

## Cấu Hình Dev

FastAPI Server chạy cục bộ tại port mặc định là `8100`.

```bash
# Khởi động (Môi trường Dev local)
source ../venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```
Swagger UI có tại: `http://localhost:8100/docs`.

## Các Route Chính (Active API)

| Endpoint | Method | Mô tả | Trạng thái |
|----------|--------|-------|------------|
| `/api/scan-prescription` | `POST` | Chạy toàn bộ Pipeline Phase A (Crop -> Deskew -> OCR -> NER -> Drug Match) trả về danh sách các loại thuốc đọc được từ ảnh. | Hoạt động chính |
| `/api/dose-verification` | `POST` | Xác minh liều lượng thuốc / Tương tác thuốc logic nâng cao hoặc phân tích thành phần viên thuốc Phase B (Hình ảnh). | Hold/Thực nghiệm |
| `/api/drug-metadata/{name}` | `GET` | (Dành cho AI Bridge tra cứu) Lấy thông tin Metadata chi tiết từ database nội bộ AI pipeline để trả về. | Internal bridge |
| `/api/drugs/search-vn` | `GET` | Tìm thuốc VN (Fallback route crawler python). Thường tính năng này đã dời qua Node. | Thường trú báo lỗi |
| `/api/drugs/search-online` | `GET` | Tìm thuốc Online. | Fallback |
| `/api/drugs/suggest-vn` | `GET` | Auto-complete suggest cho tên thuốc (Fuzzy search). | Hoạt động |
| `/api/drugs/interactions` | `POST` | Route tra cứu nhanh tương tác thuốc chéo dựa trên tên hoạt chất/thuốc (Python logic). | Hoạt động |

*(Note: Những endpoint cũ như `/api/scan-pills`, `/api/drug-info/{name}`, `/api/drugs-vn`, `/api/drugs-online` đã được deprecate hoặc routing logic đã thay thế).*

## Cold Start & Concurrency
Vì model AI như YOLOv11 và PhoBERT khá nặng, khi request đầu tiên tới `scan-prescription` có thể bị độ trễ ~15s (Model Loading warm-up). Nếu GPU mem giới hạn ~4GB (RTX 3050), server được set Semaphore giới hạn 1 concurrent connection để chặn OOM.

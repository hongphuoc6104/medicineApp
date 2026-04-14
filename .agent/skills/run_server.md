---
description: how to run the FastAPI server and test endpoints
---

# Run Server (FastAPI)

## Khởi động Server
// turbo
1. Activate venv: `source venv/bin/activate`

// turbo
2. Chạy server:
```bash
python -m server.main
```

3. Server chạy tại: `http://localhost:8100`
4. Swagger docs đầy đủ: `http://localhost:8100/docs`

## Xử lý sự cố

### Lỗi: Port 8100 already in use
// turbo
5. Kill port 8100:
```bash
fuser -k 8100/tcp
```
Sau đó chạy lại lệnh (2).

## Kiểm tra Server (Test Endpoints)

// turbo
6. Kiểm tra server up và AI sẵn sàng:
```bash
curl -X GET http://localhost:8100/api/health
```
Response mẫu: `{"status": "ok", "drug_db": 107, "ai_ready": true}`

// turbo
7. Tìm kiếm thuốc trong DB local:
```bash
curl "http://localhost:8100/api/drugs?q=paracetamol"
```

## Các Endpoints Chính

| Endpoint | Method | Mục đích |
|----------|--------|----------|
| `/api/health` | GET | Kiểm tra trạng thái server + AI |
| `/api/drugs` | GET | Tìm kiếm DB thuốc local |
| `/api/drug-info/{name}` | GET | Thông tin chi tiết 1 thuốc |
| `/api/scan-prescription` | POST | Upload ảnh đơn thuốc → nhận diện |
| `/api/drugs/search-vn` | GET | Tìm thuốc VN qua DDI Lab API |
